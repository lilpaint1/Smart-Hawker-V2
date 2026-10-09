"""Fair Allocation Engine — คำนวณและบันทึกการจัดสรรล็อกอย่างเป็นธรรม

== สูตรคะแนน (Scoring Formula) ==

  score = W_WAIT * days_waiting
        + W_ROTATION * rotation_bonus
        + W_QUOTA * quota_bonus

  W_WAIT     = 0.5  — ให้ความสำคัญกับคนรอนาน (FIFO-ish)
  W_ROTATION = 0.3  — กันคนเดิมยึดทำเลทอง (ยิ่งเคยได้บ่อย ยิ่งลดคะแนน)
  W_QUOTA    = 0.2  — โควตาผู้ค้ารายย่อย/ผู้สูงอายุ (is_verified seller w/o recent booking)

  rotation_bonus = max(0, 10 - bookings_last_90_days)  (เต็ม 10 = ไม่เคยได้เลย)
  quota_bonus    = 5 if applicant is SELLER and not booked in last 30 days else 0

== Lottery Mode ==
  seed (public) = SHA256(lot_id + date_str + salt)
  ผู้ใดก็ตรวจสอบซ้ำได้โดยใส่ seed เดิม → ได้ผลเหมือนกันทุกครั้ง

== Transparency ==
  ทุกการจัดสรรถูก INSERT ลง allocation_record พร้อม reason อ่านออก
  ห้ามแก้ไขหรือลบ (immutable ledger)
"""
import hashlib
import json
import random
import string
from datetime import datetime, timedelta, timezone

from extensions import db
from models import AllocationRecord, Booking, User, Lot, Market


# น้ำหนักสูตร (เปลี่ยนได้ตาม policy — โชว์ใน /transparency/how-it-works)
W_WAIT     = 0.5
W_ROTATION = 0.3
W_QUOTA    = 0.2
MAX_ROTATION_SCORE = 10.0


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _gen_ref() -> str:
    """สร้างเลขอ้างอิงไม่ซ้ำ เช่น SH-20260618-A4F2"""
    ts   = datetime.utcnow().strftime("%Y%m%d")
    tail = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"SH-{ts}-{tail}"


def compute_score(seller: User, bookings_last_90: int, bookings_last_30: int) -> dict:
    """คำนวณคะแนนและส่งคืน dict พร้อม breakdown"""
    # days_waiting: วันนับจาก created_at (เต็ม 30 = max)
    days_waiting = min(30, (datetime.utcnow() - seller.created_at).days)

    rotation_bonus = max(0.0, MAX_ROTATION_SCORE - bookings_last_90)
    quota_bonus    = 5.0 if (seller.role == "SELLER" and bookings_last_30 == 0) else 0.0

    score = (W_WAIT * days_waiting
           + W_ROTATION * rotation_bonus
           + W_QUOTA * quota_bonus)

    return {
        "score": round(score, 2),
        "detail": {
            "wait_days":       days_waiting,
            "rotation_bonus":  round(rotation_bonus, 2),
            "quota_bonus":     quota_bonus,
            "bookings_90d":    bookings_last_90,
            "bookings_30d":    bookings_last_30,
        }
    }


def _count_recent_bookings(seller_id: str, days: int) -> int:
    cutoff = _utcnow() - timedelta(days=days)
    return (db.session.query(Booking)
            .filter(Booking.seller_id == seller_id,
                    Booking.created_at >= cutoff,
                    Booking.status != "CANCELLED")
            .count())


def allocate_scoring(lot_id: str, applicants: list, actor: str = "system") -> list:
    """
    จัดสรรล็อกให้ผู้สมัคร (list of seller_id) โดยใช้ scoring
    ส่งคืน list ของ AllocationRecord ที่ถูก commit แล้ว (เรียงจากคะแนนสูง→ต่ำ)
    ผู้ได้รับการจัดสรร = อันดับ 1 (ถ้ามีล็อกเดียว)
    """
    lot = db.session.get(Lot, lot_id)
    if not lot:
        raise ValueError(f"Lot {lot_id} not found")
    market = db.session.get(Market, lot.market_id)

    scored = []
    for sid in applicants:
        seller = db.session.get(User, sid)
        if not seller:
            continue
        b90 = _count_recent_bookings(sid, 90)
        b30 = _count_recent_bookings(sid, 30)
        s   = compute_score(seller, b90, b30)
        scored.append((sid, s["score"], s["detail"]))

    scored.sort(key=lambda x: -x[1])

    records = []
    for rank, (sid, score, detail) in enumerate(scored):
        status = "ALLOCATED" if rank == 0 else "WAITING"
        reason = _make_reason(detail, rank == 0)
        rec = AllocationRecord(
            ref_no       = _gen_ref(),
            lot_id       = lot_id,
            market_id    = lot.market_id,
            seller_id    = sid,
            method       = "SCORING",
            score        = score,
            score_detail = json.dumps(detail, ensure_ascii=False),
            reason       = reason,
            status       = status,
            district     = market.district if market else None,
            province     = market.province if market else None,
        )
        db.session.add(rec)
        records.append(rec)

    db.session.commit()
    return records


def allocate_lottery(lot_id: str, applicants: list, public_salt: str = "") -> list:
    """
    จัดสรรล็อกแบบสลากโดยใช้ verifiable seed
    seed = SHA256(lot_id + date_str + public_salt)
    ใครก็ตรวจสอบซ้ำได้โดยใส่ seed เดิม
    """
    lot = db.session.get(Lot, lot_id)
    if not lot:
        raise ValueError(f"Lot {lot_id} not found")
    market = db.session.get(Market, lot.market_id)

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    seed_str = f"{lot_id}:{date_str}:{public_salt}"
    seed_hex = hashlib.sha256(seed_str.encode()).hexdigest()

    rng = random.Random(seed_hex)
    shuffled = list(applicants)
    rng.shuffle(shuffled)

    records = []
    for rank, sid in enumerate(shuffled):
        seller = db.session.get(User, sid)
        if not seller:
            continue
        status = "ALLOCATED" if rank == 0 else "WAITING"
        reason = (f"จัดสรรด้วยสลาก (seed สาธารณะ: {seed_hex[:12]}...) — "
                  + ("ได้รับการจัดสรร อันดับ 1" if rank == 0 else f"อยู่ลำดับสำรอง {rank+1}"))
        rec = AllocationRecord(
            ref_no       = _gen_ref(),
            lot_id       = lot_id,
            market_id    = lot.market_id,
            seller_id    = sid,
            method       = "LOTTERY",
            score        = None,
            score_detail = json.dumps({"rank": rank+1, "total": len(shuffled)}, ensure_ascii=False),
            reason       = reason,
            lottery_seed = seed_hex,
            status       = status,
            district     = market.district if market else None,
            province     = market.province if market else None,
        )
        db.session.add(rec)
        records.append(rec)

    db.session.commit()
    return records


def record_booking_allocation(booking) -> AllocationRecord:
    """เขียน ledger อัตโนมัติเมื่อมีการจอง (method=AUTO_BOOKING)"""
    lot    = db.session.get(Lot,    booking.lot_id)
    market = db.session.get(Market, lot.market_id) if lot else None
    rec = AllocationRecord(
        ref_no       = _gen_ref(),
        lot_id       = booking.lot_id,
        market_id    = lot.market_id if lot else None,
        seller_id    = booking.seller_id,
        booking_id   = booking.id,
        method       = "AUTO_BOOKING",
        score        = None,
        reason       = "จองผ่านระบบปกติ (ใครกดก่อนได้ก่อน)",
        status       = "ALLOCATED",
        district     = market.district if market else None,
        province     = market.province if market else None,
    )
    db.session.add(rec)
    db.session.commit()
    return rec


def _make_reason(detail: dict, winner: bool) -> str:
    parts = []
    if detail.get("wait_days", 0) > 0:
        parts.append(f"รอคิว {detail['wait_days']} วัน (+{W_WAIT * detail['wait_days']:.1f} คะแนน)")
    rb = detail.get("rotation_bonus", 0)
    if rb > 0:
        parts.append(f"โบนัสหมุนเวียน +{W_ROTATION * rb:.1f}")
    qb = detail.get("quota_bonus", 0)
    if qb > 0:
        parts.append(f"โควตาผู้ค้ารายย่อย +{W_QUOTA * qb:.1f}")
    summary = " | ".join(parts) if parts else "คะแนนพื้นฐาน"
    return ("ได้รับการจัดสรร — " if winner else "อยู่ในรายชื่อสำรอง — ") + summary


def compute_transparency_index(market_id: str) -> float:
    """
    ดัชนีความโปร่งใส 0–100 คำนวณจาก:
      - สัดส่วนการจัดสรรที่มีเหตุผล (reason ไม่ว่าง) / ทั้งหมด  * 50
      - สัดส่วน SCORING+LOTTERY vs AUTO_BOOKING * 30
      - สัดส่วนล็อกที่มีข้อมูลสาธารณะ * 20
    """
    total = db.session.query(AllocationRecord).filter_by(market_id=market_id).count()
    if total == 0:
        return 50.0  # default midpoint สำหรับตลาดใหม่

    with_reason = (db.session.query(AllocationRecord)
                   .filter(AllocationRecord.market_id == market_id,
                           AllocationRecord.reason != None,
                           AllocationRecord.reason != "")
                   .count())
    scored = (db.session.query(AllocationRecord)
              .filter(AllocationRecord.market_id == market_id,
                      AllocationRecord.method.in_(["SCORING", "LOTTERY"]))
              .count())

    ratio_reason = with_reason / total
    ratio_scored = scored / total

    market = db.session.get(Market, market_id)
    has_zone = bool(market and getattr(market, "zone", None))

    score = (ratio_reason * 50) + (ratio_scored * 30) + (20 if has_zone else 0)
    return round(min(100, max(0, score)), 1)
