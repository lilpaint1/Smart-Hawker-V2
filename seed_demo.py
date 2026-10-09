"""
seed_demo.py — Demo seed สำหรับ Smart Hawker
รัน: python seed_demo.py

สร้างข้อมูลสาธิต:
  - 1 owner, 10 sellers (ชื่อไทย)
  - 6 ตลาด (กรุงเทพฯ)
  - แต่ละตลาด 8 ล็อก
  - 15 bookings
  - 20 AllocationRecords (mix SCORING, LOTTERY, AUTO_BOOKING)
  - ZoneData สำหรับทุกตลาด (2 RED, 2 YELLOW, 2 GREEN)
"""
import os
import sys
import json
import random
import hashlib
import string
from datetime import datetime, timedelta, timezone

# ตั้ง env ก่อน import app
os.environ.setdefault("SECRET_KEY", "demo-seed-secret")
os.environ.setdefault("ENABLE_QUICK_LOGIN", "1")

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from extensions import db
from models import (User, Market, Lot, Booking, Payment,
                    AllocationRecord, ZoneData, new_id)


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def days_ago(n):
    return utcnow() - timedelta(days=n)


def gen_ref():
    ts   = datetime.utcnow().strftime("%Y%m%d")
    tail = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"SH-{ts}-{tail}"


# ---- ข้อมูลตัวอย่าง ----
OWNER_DATA = {
    "name": "สมศักดิ์ จัดการตลาด",
    "phone": "0811111111",
    "role": "MARKET_OWNER",
    "is_verified": True,
}

SELLERS = [
    {"name": "มาลี ขยันค้า",      "phone": "0821111111", "shop_name": "ก๋วยเตี๋ยวมาลี",   "product_type": "อาหาร"},
    {"name": "สมชาย ผักสด",       "phone": "0821111112", "shop_name": "ผักสดสมชาย",       "product_type": "ผัก"},
    {"name": "ประยุทธ ของสด",     "phone": "0821111113", "shop_name": "ปลาสดประยุทธ",     "product_type": "อาหารทะเล"},
    {"name": "วิไล ขนมหวาน",      "phone": "0821111114", "shop_name": "ขนมไทยวิไล",      "product_type": "ขนม"},
    {"name": "บุญมี เสื้อผ้า",    "phone": "0821111115", "shop_name": "เสื้อผ้าบุญมี",   "product_type": "เสื้อผ้า"},
    {"name": "สุดา ผลไม้",        "phone": "0821111116", "shop_name": "ผลไม้สดสุดา",      "product_type": "ผลไม้"},
    {"name": "ธงชัย ของใช้",      "phone": "0821111117", "shop_name": "ของใช้ราคาถูก",   "product_type": "ของใช้"},
    {"name": "จันทร์ทิพย์ กาแฟ",  "phone": "0821111118", "shop_name": "กาแฟโบราณจันทร์", "product_type": "เครื่องดื่ม"},
    {"name": "อนุชา ข้าวมันไก่",  "phone": "0821111119", "shop_name": "ข้าวมันไก่อนุชา", "product_type": "อาหาร"},
    {"name": "นงลักษณ์ ผ้าพื้น",  "phone": "0821111120", "shop_name": "ผ้าพื้นเมือง",    "product_type": "ผ้า"},
]

MARKETS = [
    # ── ภาครัฐ (GOV) ──────────────────────────────────────────────
    {
        "name": "พื้นที่ค้าขายสวนลุมพินี",
        "district": "ปทุมวัน",
        "province": "กรุงเทพมหานคร",
        "lat": 13.7300, "lng": 100.5418,
        "description": "พื้นที่ค้าขายริมสวนลุมพินี เปิดโดย กทม. ภายใต้นโยบายชัชชาติ — ส่งเสริมพ่อค้าแม่ค้ารายย่อย จัดสรรอย่างโปร่งใส",
        "opening_hours": "อ-อา 07:00-19:00",
        "tags": "ภาครัฐ,สวนสาธารณะ,ของกิน,สตรีทฟู้ด",
        "owner_type": "GOV",
        "gov_ref": "BMA-LUM-2024-001",
        "zone": {"sidewalk": 4.0, "max_capacity": 20, "complaints": 1, "traffy": 0, "level": "GREEN",
                 "note": "พื้นที่กว้าง จัดระเบียบโดย กทม. ทางเท้าเพียงพอ"},
    },
    {
        "name": "ตลาดอตก.",
        "district": "จตุจักร",
        "province": "กรุงเทพมหานคร",
        "lat": 13.8195, "lng": 100.5500,
        "description": "ตลาดนัดสวนจตุจักร แหล่งค้าขายสุดสัปดาห์ที่ใหญ่ที่สุด — บริหารร่วม อบต. จตุจักร",
        "opening_hours": "ส-อา 09:00-18:00",
        "tags": "ของสะสม,เสื้อผ้า,ต้นไม้,สัตว์เลี้ยง",
        "owner_type": "GOV",
        "gov_ref": "BMA-JJK-2023-007",
        "zone": {"sidewalk": 3.5, "max_capacity": 16, "complaints": 2, "traffy": 1, "level": "GREEN",
                 "note": "พื้นที่กว้างขวาง บริหารจัดการดี"},
    },
    # ── เอกชน (PRIVATE) ───────────────────────────────────────────
    {
        "name": "ตลาดคลองเตย",
        "district": "คลองเตย",
        "province": "กรุงเทพมหานคร",
        "lat": 13.7160, "lng": 100.5620,
        "description": "ตลาดสดคลองเตย ศูนย์กลางการค้าส่งของกรุงเทพฯ",
        "opening_hours": "จ-อา 04:00-14:00",
        "tags": "ผัก,ผลไม้,ของสด,อาหาร",
        "owner_type": "PRIVATE",
        "gov_ref": None,
        "zone": {"sidewalk": 1.8, "max_capacity": 8, "complaints": 7, "traffy": 5, "level": "RED",
                 "note": "ทางเท้าแคบมาก ร้องเรียนสูง"},
    },
    {
        "name": "ตลาดมีนบุรี",
        "district": "มีนบุรี",
        "province": "กรุงเทพมหานคร",
        "lat": 13.8066, "lng": 100.7490,
        "description": "ตลาดชุมชนฝั่งตะวันออก อาหารทะเลสด",
        "opening_hours": "จ-อา 06:00-12:00",
        "tags": "อาหารทะเล,ผัก,อาหาร",
        "owner_type": "PRIVATE",
        "gov_ref": None,
        "zone": {"sidewalk": 2.2, "max_capacity": 10, "complaints": 4, "traffy": 3, "level": "YELLOW",
                 "note": "ชั่วโมงเร่งด่วนเช้าแน่น"},
    },
    {
        "name": "ตลาดลาดพร้าว",
        "district": "ลาดพร้าว",
        "province": "กรุงเทพมหานคร",
        "lat": 13.8070, "lng": 100.5930,
        "description": "ตลาดสดใจกลางลาดพร้าว",
        "opening_hours": "จ-อา 05:00-12:00",
        "tags": "ผัก,อาหาร,ขนม",
        "owner_type": "PRIVATE",
        "gov_ref": None,
        "zone": {"sidewalk": 2.0, "max_capacity": 8, "complaints": 6, "traffy": 4, "level": "RED",
                 "note": "ความหนาแน่นสูง ติดถนนใหญ่"},
    },
    {
        "name": "ตลาดรัตนาธิเบศร์",
        "district": "บางกรวย",
        "province": "นนทบุรี",
        "lat": 13.8535, "lng": 100.4840,
        "description": "ตลาดชุมชนนนทบุรี ของสดราคาถูก",
        "opening_hours": "จ-ศ 05:30-11:00",
        "tags": "ผัก,ผลไม้,ของสด",
        "owner_type": "PRIVATE",
        "gov_ref": None,
        "zone": {"sidewalk": 3.0, "max_capacity": 14, "complaints": 1, "traffy": 0, "level": "GREEN",
                 "note": "ทางเท้ากว้าง บรรยากาศดี"},
    },
    {
        "name": "ตลาดบางแค",
        "district": "บางแค",
        "province": "กรุงเทพมหานคร",
        "lat": 13.7140, "lng": 100.4030,
        "description": "ตลาดชุมชนฝั่งธนบุรี",
        "opening_hours": "จ-อา 05:00-13:00",
        "tags": "ผัก,อาหาร,เสื้อผ้า",
        "owner_type": "PRIVATE",
        "gov_ref": None,
        "zone": {"sidewalk": 2.5, "max_capacity": 12, "complaints": 3, "traffy": 2, "level": "YELLOW",
                 "note": "ปานกลาง — จัดระเบียบแล้วบางส่วน"},
    },
]


def run():
    app = create_app()
    with app.app_context():
        print("กำลังล้างและสร้างฐานข้อมูลใหม่...")
        db.drop_all()
        db.create_all()

        # ---- Users ----
        owner = User(
            id=new_id(), name=OWNER_DATA["name"], phone=OWNER_DATA["phone"],
            role=OWNER_DATA["role"], is_verified=True,
            created_at=days_ago(120),
        )
        db.session.add(owner)

        sellers = []
        for i, sd in enumerate(SELLERS):
            s = User(
                id=new_id(), name=sd["name"], phone=sd["phone"], role="SELLER",
                shop_name=sd["shop_name"], product_type=sd["product_type"],
                is_verified=(i < 5),
                created_at=days_ago(random.randint(10, 90)),
            )
            db.session.add(s)
            sellers.append(s)

        db.session.flush()

        # ---- Markets + Lots + Zones ----
        markets = []
        all_lots = []
        for md in MARKETS:
            m = Market(
                id=new_id(), owner_id=owner.id,
                name=md["name"], description=md["description"],
                province=md["province"], district=md["district"],
                lat=md["lat"], lng=md["lng"],
                opening_hours=md["opening_hours"],
                tags=md["tags"],
                owner_type=md.get("owner_type", "PRIVATE"),
                gov_ref=md.get("gov_ref"),
                is_verified=True,
                avg_rating=round(random.uniform(3.5, 5.0), 1),
                review_count=random.randint(5, 80),
                popularity=random.randint(50, 500),
                created_at=days_ago(random.randint(30, 180)),
            )
            db.session.add(m)
            markets.append(m)
            db.session.flush()

            # Lots
            for j in range(1, 9):
                prefix = ["A","B","C","D","E","F","G","H"][j-1]
                l = Lot(
                    id=new_id(), market_id=m.id,
                    code=f"{prefix}{random.randint(1,9)}",
                    price_per_day=random.choice([150, 200, 250, 300, 350, 400, 500]),
                    rent_type=random.choice(["DAILY", "DAILY", "DAILY", "WEEKLY", "MONTHLY"]),
                    status="AVAILABLE",
                )
                db.session.add(l)
                all_lots.append((l, m))

            # Zone Data
            zd_info = md["zone"]
            zd = ZoneData(
                id=new_id(), market_id=m.id,
                sidewalk_width_m=zd_info["sidewalk"],
                max_capacity=zd_info["max_capacity"],
                complaints_count=zd_info["complaints"],
                traffy_issues=zd_info["traffy"],
                density_level=zd_info["level"],
                note=zd_info["note"],
                updated_at=days_ago(random.randint(0, 7)),
            )
            db.session.add(zd)

        db.session.flush()

        # ---- Bookings (15) ----
        bookings = []
        random.shuffle(all_lots)
        for i in range(15):
            lot, mkt = all_lots[i % len(all_lots)]
            seller = random.choice(sellers)
            start  = days_ago(random.randint(0, 60))
            dep    = max(50, round(lot.price_per_day * 0.2))
            b = Booking(
                id=new_id(), lot_id=lot.id, seller_id=seller.id,
                date=start, start_date=start,
                deposit_amount=dep,
                status=random.choice(["CONFIRMED", "CONFIRMED", "CONFIRMED", "PENDING", "CANCELLED"]),
                payment_status=random.choice(["PAID", "PAID", "PENDING"]),
                created_at=start,
            )
            db.session.add(b)
            bookings.append((b, lot, mkt, seller))

        db.session.flush()

        # ---- AllocationRecords (20) ----
        # Mix: 8 SCORING, 6 LOTTERY, 6 AUTO_BOOKING
        def make_scoring_reason(detail, winner):
            parts = []
            if detail.get("wait_days", 0) > 0:
                parts.append(f"รอคิว {detail['wait_days']} วัน (+{0.5 * detail['wait_days']:.1f} คะแนน)")
            if detail.get("rotation_bonus", 0) > 0:
                parts.append(f"โบนัสหมุนเวียน +{0.3 * detail['rotation_bonus']:.1f}")
            if detail.get("quota_bonus", 0) > 0:
                parts.append(f"โควตาผู้ค้ารายย่อย +{0.2 * detail['quota_bonus']:.1f}")
            summary = " | ".join(parts) or "คะแนนพื้นฐาน"
            return ("ได้รับการจัดสรร — " if winner else "อยู่ในรายชื่อสำรอง — ") + summary

        alloc_records = []

        # SCORING records
        for i in range(8):
            lot, mkt = random.choice(all_lots)
            seller   = random.choice(sellers)
            wait_d   = random.randint(1, 28)
            rot_b    = random.uniform(0, 10)
            quota_b  = random.choice([0, 0, 5])
            score    = round(0.5*wait_d + 0.3*rot_b + 0.2*quota_b, 2)
            detail   = {"wait_days": wait_d, "rotation_bonus": round(rot_b,2), "quota_bonus": quota_b,
                        "bookings_90d": max(0, 10 - int(rot_b)), "bookings_30d": 0 if quota_b else 1}
            winner   = (i % 3 != 2)  # roughly 2/3 ALLOCATED
            status   = "ALLOCATED" if winner else "WAITING"
            rec = AllocationRecord(
                id=new_id(), ref_no=gen_ref(),
                lot_id=lot.id, market_id=mkt.id, seller_id=seller.id,
                method="SCORING", score=score,
                score_detail=json.dumps(detail, ensure_ascii=False),
                reason=make_scoring_reason(detail, winner),
                status=status,
                district=mkt.district, province=mkt.province,
                allocated_at=days_ago(random.randint(0, 45)),
            )
            db.session.add(rec)
            alloc_records.append(rec)

        # LOTTERY records
        for i in range(6):
            lot, mkt = random.choice(all_lots)
            seller   = random.choice(sellers)
            seed_hex = hashlib.sha256(f"{lot.id}:demo:{i}".encode()).hexdigest()
            rank     = random.randint(0, 4)
            status   = "ALLOCATED" if rank == 0 else "WAITING"
            rec = AllocationRecord(
                id=new_id(), ref_no=gen_ref(),
                lot_id=lot.id, market_id=mkt.id, seller_id=seller.id,
                method="LOTTERY", score=None,
                score_detail=json.dumps({"rank": rank+1, "total": 5}, ensure_ascii=False),
                reason=f"จัดสรรด้วยสลาก (seed สาธารณะ: {seed_hex[:12]}...) — " +
                       ("ได้รับการจัดสรร อันดับ 1" if rank == 0 else f"อยู่ลำดับสำรอง {rank+1}"),
                lottery_seed=seed_hex,
                status=status,
                district=mkt.district, province=mkt.province,
                allocated_at=days_ago(random.randint(0, 30)),
            )
            db.session.add(rec)
            alloc_records.append(rec)

        # AUTO_BOOKING records from bookings
        for b, lot, mkt, seller in bookings[:6]:
            rec = AllocationRecord(
                id=new_id(), ref_no=gen_ref(),
                lot_id=lot.id, market_id=mkt.id, seller_id=seller.id,
                booking_id=b.id,
                method="AUTO_BOOKING", score=None,
                reason="จองผ่านระบบปกติ (ใครกดก่อนได้ก่อน)",
                status="ALLOCATED",
                district=mkt.district, province=mkt.province,
                allocated_at=b.created_at,
            )
            db.session.add(rec)
            alloc_records.append(rec)

        db.session.commit()

        # Summary
        m_count = db.session.query(Market).count()
        a_count = db.session.query(AllocationRecord).count()
        z_count = db.session.query(ZoneData).count()
        s_count = db.session.query(User).filter_by(role="SELLER").count()
        b_count = db.session.query(Booking).count()
        l_count = db.session.query(Lot).count()

        gov_count = db.session.query(Market).filter_by(owner_type="GOV").count()
        priv_count = db.session.query(Market).filter_by(owner_type="PRIVATE").count()
        print(f"[OK] seed_demo done:")
        print(f"     {m_count} พื้นที่ ({gov_count} ภาครัฐ, {priv_count} เอกชน), {l_count} ล็อก, {s_count} ผู้ค้า")
        print(f"     {b_count} bookings, {a_count} allocation records, {z_count} zone data")
        print()
        print("เปิด: python app.py")
        print("จากนั้นเข้า: http://localhost:5000")


if __name__ == "__main__":
    run()
