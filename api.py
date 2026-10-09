"""API ทั้งหมดอยู่ที่นี่ (Blueprint /api). ทุก endpoint ทำตามแพทเทิร์นเดียวกัน:
   รับ JSON -> ตรวจข้อมูล -> เช็คสิทธิ์ -> คุย DB -> ตอบ ok()/fail()
"""
import os
import io
import csv
import hmac
import hashlib
import random
import json
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from io import BytesIO
import qrcode
from flask import Blueprint, request, session, send_file
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

from extensions import db
from models import (User, Market, Lot, Booking, Payment, Review,
                    Message, Notification, OtpCode, Favorite, AuditLog,
                    AllocationRecord, ZoneData)
import allocation as alloc_engine
from constants import RENT_TYPES, ROLES
from helpers import (ok, fail, current_user, login_required, admin_required,
                     gen_otp, hash_otp, otp_expiry, valid_phone, deposit_for,
                     write_audit, compute_market_ratings, refresh_market_rating)
from sms import send_sms
from promptpay import generate_payload

api = Blueprint("api", __name__, url_prefix="/api")

# ---- UTC helper — naive datetime consistent with SQLite storage ----
def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

# ---- Admin login rate limiting (in-memory, single process) ----
_admin_fail_times: dict = defaultdict(list)
_ADMIN_MAX_FAILS    = 5
_ADMIN_LOCKOUT_SECS = 300   # 5 min

def _admin_locked(ip: str) -> bool:
    now = time.time()
    _admin_fail_times[ip] = [t for t in _admin_fail_times[ip] if now - t < _ADMIN_LOCKOUT_SECS]
    return len(_admin_fail_times[ip]) >= _ADMIN_MAX_FAILS

def _admin_fail_record(ip: str) -> None:
    _admin_fail_times[ip].append(time.time())


# ---- OTP IP rate limiting — max 5 per IP per 10 minutes ----
_otp_ip_times: dict = defaultdict(list)
_OTP_IP_MAX    = 5
_OTP_IP_WINDOW = 600  # 10 min

def _otp_ip_allowed(ip: str) -> bool:
    now = time.time()
    _otp_ip_times[ip] = [t for t in _otp_ip_times[ip] if now - t < _OTP_IP_WINDOW]
    if len(_otp_ip_times[ip]) >= _OTP_IP_MAX:
        return False
    _otp_ip_times[ip].append(now)
    return True


# ============ ตัวช่วยแปลง model -> dict ============
def user_full(u):
    return {
        "id": u.id, "name": u.name, "phone": u.phone, "role": u.role,
        "shopName": u.shop_name, "productType": u.product_type, "bio": u.bio,
        "isVerified": u.is_verified, "isSuspended": u.is_suspended,
        "createdAt": u.created_at.isoformat(),
        "verificationStatus": getattr(u, "verification_status", "UNVERIFIED"),
        "verifiedName": getattr(u, "verified_name", None),
    }


def lot_dto(l):
    return {
        "id": l.id, "code": l.code, "pricePerDay": l.price_per_day,
        "rentType": l.rent_type, "status": l.status, "note": l.note,
    }


def market_item(m, rating_map=None, fav_ids=None):
    avail  = [l for l in m.lots if l.status == "AVAILABLE"]
    prices = [l.price_per_day for l in avail]
    avg, cnt = (rating_map or {}).get(m.id, (m.avg_rating or 0.0, m.review_count or 0))
    return {
        "id": m.id, "name": m.name, "province": m.province,
        "district": m.district, "lat": m.lat, "lng": m.lng,
        "coverPhotoUrl": m.cover_photo_url, "tags": m.tag_list(),
        "popularity": m.popularity, "openingHours": m.opening_hours,
        "avgRating": avg, "reviewCount": cnt,
        "isVerified": m.is_verified, "isFeatured": m.is_featured,
        "minPrice": min(prices) if prices else None,
        "availableLots": len(avail), "totalLots": len(m.lots),
        "isFav": m.id in (fav_ids or set()),
        "ownerVerified": (getattr(m.owner, "verification_status", "UNVERIFIED") == "VERIFIED"
                          if m.owner else False),
        "ownerType": getattr(m, "owner_type", "PRIVATE") or "PRIVATE",
        "govRef":    getattr(m, "gov_ref", None),
    }


def is_console_sms():
    return os.environ.get("SMS_PROVIDER", "console") == "console"


# ============ AUTH ============
@api.post("/auth/register")
def register():
    d = request.get_json(silent=True) or {}
    name, phone = (d.get("name") or "").strip(), (d.get("phone") or "").strip()
    role, email = d.get("role"), (d.get("email") or "").strip()
    if len(name) < 2:
        return fail("กรุณากรอกชื่อ (อย่างน้อย 2 ตัวอักษร)")
    if not valid_phone(phone):
        return fail("เบอร์โทรต้องเป็นตัวเลข 10 หลัก เช่น 0812345678")
    if role not in ("SELLER", "MARKET_OWNER"):
        return fail("กรุณาเลือกประเภทผู้ใช้")
    if User.query.filter_by(phone=phone).first():
        return fail("เบอร์นี้สมัครแล้ว กรุณาเข้าสู่ระบบ", 409)

    db.session.add(User(name=name, phone=phone, email=email or None, role=role))
    code = gen_otp()
    db.session.add(OtpCode(phone=phone, code_hash=hash_otp(phone, code),
                           expires_at=otp_expiry()))
    db.session.commit()
    sms_r = send_sms(phone, f"Smart Hawker: รหัสยืนยัน OTP คือ {code} (หมดอายุ 5 นาที)")
    if not sms_r.get("ok") and not sms_r.get("dev"):
        return fail("ส่ง SMS ไม่สำเร็จ กรุณาลองใหม่ หรือติดต่อผู้ดูแลระบบ")
    return ok({"phone": phone, "dev": code if is_console_sms() else None})


@api.post("/auth/otp/request")
def otp_request():
    # IP-based rate limit: max 5 OTP requests per IP per 10 minutes
    ip = request.remote_addr or "0.0.0.0"
    if not _otp_ip_allowed(ip):
        return fail("ขอ OTP บ่อยเกินไป กรุณารอ 10 นาทีแล้วลองใหม่", 429)
    d = request.get_json(silent=True) or {}
    phone = (d.get("phone") or "").strip()
    if not valid_phone(phone):
        return fail("เบอร์โทรไม่ถูกต้อง")
    u = User.query.filter_by(phone=phone).first()
    if not u:
        return fail("ไม่พบเบอร์นี้ในระบบ กรุณาสมัครก่อน", 404)
    if u.is_suspended:
        return fail("บัญชีนี้ถูกระงับการใช้งาน กรุณาติดต่อผู้ดูแล", 403)
    # Rate limit: max 1 OTP per 60 seconds per phone
    recent = OtpCode.query.filter_by(phone=phone).order_by(OtpCode.created_at.desc()).first()
    if recent:
        elapsed = (_utcnow() - recent.created_at).total_seconds()
        if elapsed < 60:
            return fail(f"กรุณารอ {max(1, int(60 - elapsed))} วินาทีก่อนขอ OTP ใหม่")
    code = gen_otp()
    db.session.add(OtpCode(phone=phone, code_hash=hash_otp(phone, code),
                           expires_at=otp_expiry()))
    db.session.commit()
    sms_r = send_sms(phone, f"Smart Hawker: รหัสเข้าสู่ระบบ OTP คือ {code} (หมดอายุ 5 นาที)")
    if not sms_r.get("ok") and not sms_r.get("dev"):
        return fail("ส่ง SMS ไม่สำเร็จ กรุณาลองใหม่ หรือติดต่อผู้ดูแลระบบ")
    return ok({"phone": phone, "dev": code if is_console_sms() else None})


@api.post("/auth/otp/verify")
def otp_verify():
    d = request.get_json(silent=True) or {}
    phone, code = (d.get("phone") or "").strip(), (d.get("code") or "").strip()
    otp = (OtpCode.query
           .filter_by(phone=phone, consumed=False)
           .filter(OtpCode.expires_at > _utcnow())
           .order_by(OtpCode.created_at.desc()).first())
    if not otp:
        return fail("รหัส OTP หมดอายุหรือไม่ถูกต้อง กรุณาขอรหัสใหม่", 401)
    if otp.attempts >= 5:
        otp.consumed = True
        db.session.commit()
        return fail("รหัส OTP ถูกใช้งานผิดพลาดเกินกำหนด กรุณาขอรหัสใหม่", 401)
    otp.attempts = (otp.attempts or 0) + 1
    if otp.code_hash != hash_otp(phone, code):
        if otp.attempts >= 5:
            otp.consumed = True
        db.session.commit()
        return fail("รหัส OTP ไม่ถูกต้อง", 401)
    user = User.query.filter_by(phone=phone).first()
    if not user:
        return fail("ไม่พบผู้ใช้", 404)
    if user.is_suspended:
        return fail("บัญชีนี้ถูกระงับการใช้งาน", 403)
    otp.consumed = True
    db.session.commit()
    session.clear()
    session["user_id"], session["role"], session["name"] = user.id, user.role, user.name
    return ok({"role": user.role})


@api.post("/auth/admin")
def admin_login():
    ip = request.remote_addr or "0.0.0.0"
    if _admin_locked(ip):
        return fail("พยายามเข้าสู่ระบบหลายครั้งเกินไป กรุณารอ 5 นาที", 429)
    code_hash_env  = os.environ.get("ADMIN_CODE_HASH", "")
    code_plain_env = os.environ.get("ADMIN_CODE", "")
    if not code_hash_env and not code_plain_env:
        return fail("ระบบแอดมินถูกปิดใช้งาน (ADMIN_CODE ยังไม่ได้ตั้งค่า)", 503)
    d = request.get_json(silent=True) or {}
    submitted_hash = hashlib.sha256((d.get("code") or "").encode()).hexdigest()
    stored_hash    = code_hash_env or hashlib.sha256(code_plain_env.encode()).hexdigest()
    if not hmac.compare_digest(stored_hash, submitted_hash):
        _admin_fail_record(ip)
        return fail("รหัสแอดมินไม่ถูกต้อง", 401)
    _admin_fail_times.pop(ip, None)
    session.clear()
    session["role"], session["name"] = "ADMIN", "ผู้ดูแลระบบ"
    write_audit("ADMIN_LOGIN")
    db.session.commit()
    return ok({"role": "ADMIN"})


@api.post("/auth/quick")
def quick_login():
    """PROTOTYPE: เข้าระบบไวไม่ต้อง OTP (ปิดด้วย ENABLE_QUICK_LOGIN=0)"""
    if os.environ.get("ENABLE_QUICK_LOGIN", "1") == "0":
        return fail("quick login ถูกปิดอยู่", 403)
    d = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip() or "ผู้ทดลอง"
    role = d.get("role")
    if role not in ("SELLER", "MARKET_OWNER"):
        return fail("เลือกบทบาทไม่ถูกต้อง")
    phone = "09" + f"{random.randint(0, 99999999):08d}"
    while User.query.filter_by(phone=phone).first():
        phone = "09" + f"{random.randint(0, 99999999):08d}"
    u = User(name=name, phone=phone, role=role, bio="(บัญชีทดลอง prototype)")
    db.session.add(u)
    db.session.commit()
    session.clear()
    session["user_id"], session["role"], session["name"] = u.id, u.role, u.name
    return ok({"role": u.role})


@api.post("/auth/logout")
def logout():
    session.clear()
    return ok()


@api.get("/me")
def me():
    uid, role = session.get("user_id"), session.get("role")
    if not role:
        return ok({"session": None, "user": None})
    u = current_user()
    return ok({"session": {"userId": uid, "role": role, "name": session.get("name")},
               "user": user_full(u) if u else None})


@api.delete("/me")
@login_required
def delete_account():
    """ผู้ใช้ลบบัญชีตนเอง"""
    u = current_user()
    for m in list(u.markets):
        db.session.delete(m)
    Booking.query.filter_by(seller_id=u.id).delete()
    Review.query.filter_by(from_user_id=u.id).delete()
    Message.query.filter((Message.from_user_id == u.id) | (Message.to_user_id == u.id)).delete()
    Notification.query.filter_by(user_id=u.id).delete()
    Favorite.query.filter_by(user_id=u.id).delete()
    OtpCode.query.filter_by(phone=u.phone).delete()
    db.session.delete(u)
    db.session.commit()
    session.clear()
    return ok({"deleted": True})


# ============ MARKETS ============
@api.get("/markets")
def markets_list():
    q         = (request.args.get("q") or "").strip()
    province  = (request.args.get("province") or "").strip()
    rent_type = request.args.get("rentType") or ""
    max_price = request.args.get("maxPrice", type=float)
    min_price = request.args.get("minPrice", type=float)
    sort      = request.args.get("sort", "popularity")  # popularity|price|rating
    only_avail = request.args.get("available") == "1"
    limit      = request.args.get("limit", type=int)

    query = Market.query.options(selectinload(Market.lots), joinedload(Market.owner))
    if province:
        query = query.filter(Market.province.contains(province))
    if q:
        query = query.filter(Market.name.contains(q))
    if sort == "rating":
        query = query.order_by(Market.avg_rating.desc())
    elif sort == "price":
        query = query.order_by(Market.avg_rating)   # fallback — price is on lots
    else:
        query = query.order_by(Market.popularity.desc())
    if limit:
        query = query.limit(limit)
    markets = query.all()

    # batch rating lookup
    mid_list = [m.id for m in markets]
    rating_map = compute_market_ratings(mid_list)

    # fav ids for logged-in user
    fav_ids = set()
    uid = session.get("user_id")
    if uid:
        favs = Favorite.query.filter_by(user_id=uid).with_entities(Favorite.market_id).all()
        fav_ids = {f.market_id for f in favs}

    items = []
    for m in markets:
        matching = [l for l in m.lots
                    if (max_price is None or l.price_per_day <= max_price)
                    and (min_price is None or l.price_per_day >= min_price)
                    and (not rent_type or l.rent_type == rent_type)
                    and (not only_avail or l.status == "AVAILABLE")]
        if (max_price is not None or min_price is not None or rent_type or only_avail) and not matching:
            continue
        items.append(market_item(m, rating_map, fav_ids))
    return ok({"markets": items})


@api.get("/markets/featured")
def markets_featured():
    """Top markets for homepage — ไม่ต้อง login"""
    ms = Market.query.order_by(Market.popularity.desc()).limit(8).all()
    mid_list = [m.id for m in ms]
    rating_map = compute_market_ratings(mid_list)
    return ok({"markets": [market_item(m, rating_map) for m in ms]})


@api.post("/markets")
@login_required
def market_create():
    if session.get("role") not in ("MARKET_OWNER", "ADMIN"):
        return fail("เฉพาะเจ้าของตลาด", 403)
    d = request.get_json(silent=True) or {}
    if len((d.get("name") or "").strip()) < 2:
        return fail("กรุณากรอกชื่อตลาด")
    if not d.get("province"):
        return fail("กรุณาระบุจังหวัด")
    try:
        lat, lng = float(d["lat"]), float(d["lng"])
    except (KeyError, TypeError, ValueError):
        return fail("กรุณาปักหมุดตำแหน่งบนแผนที่")
    if session.get("role") == "ADMIN" and d.get("ownerId"):
        owner = User.query.get(d["ownerId"])
        if not owner:
            return fail("ไม่พบเจ้าของตลาดที่ระบุ", 404)
        owner_id = owner.id
    else:
        owner_id = session["user_id"] if session.get("role") != "ADMIN" else (session.get("user_id") or "ADMIN")
    import re as _re
    raw_cover = (d.get("coverPhotoUrl") or "").strip()
    safe_cover = raw_cover if _re.match(r"^https?://", raw_cover, _re.IGNORECASE) else None
    m = Market(
        owner_id=owner_id,
        name=d["name"].strip(),
        description=(d.get("description") or "").strip() or None,
        province=d["province"].strip(),
        district=(d.get("district") or "").strip() or None,
        lat=lat, lng=lng,
        opening_hours=(d.get("openingHours") or "").strip() or None,
        tags=(d.get("tags") or "").strip() or None,
        cover_photo_url=safe_cover,
    )
    db.session.add(m)
    db.session.commit()
    return ok({"marketId": m.id})


@api.get("/markets/<mid>")
def market_detail(mid):
    m = Market.query.get(mid)
    if not m:
        return fail("ไม่พบตลาด", 404)
    rating_map = compute_market_ratings([mid])
    fav_ids = set()
    uid = session.get("user_id")
    if uid:
        f = Favorite.query.filter_by(user_id=uid, market_id=mid).first()
        if f: fav_ids.add(mid)
    item = market_item(m, rating_map, fav_ids)
    item.update({
        "description": m.description,
        "openingHours": m.opening_hours,
        "tags": m.tag_list(),
        "ownerId": m.owner_id,
        "ownerName": m.owner.name,
        "ownerVerified": m.owner.is_verified,
        "lots": [lot_dto(l) for l in sorted(m.lots, key=lambda x: x.code)],
    })
    # bump popularity — session-keyed dedup to prevent inflate-on-refresh
    view_key = f"viewed_{mid}"
    if not session.get(view_key):
        session[view_key] = True
        m.popularity = (m.popularity or 0) + 1
        db.session.commit()
    return ok({"market": item})


@api.post("/markets/<mid>/cover")
@login_required
def upload_market_cover(mid):
    """อัปโหลดรูปหน้าปกตลาด — เฉพาะเจ้าของตลาดหรือแอดมิน"""
    import uuid
    m = Market.query.get(mid)
    if not m:
        return fail("ไม่พบตลาด", 404)
    if session.get("role") != "ADMIN" and m.owner_id != session.get("user_id"):
        return fail("ไม่มีสิทธิ์", 403)
    if "file" not in request.files:
        return fail("ไม่พบไฟล์")
    f = request.files["file"]
    if not f.content_type or not f.content_type.startswith("image/"):
        return fail("ไฟล์ต้องเป็นรูปภาพ")
    ext = f.filename.rsplit(".", 1)[-1].lower() if f.filename and "." in f.filename else "jpg"
    if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
        return fail("นามสกุลไฟล์ไม่รองรับ")
    fname = uuid.uuid4().hex + "." + ext
    upload_dir = os.path.join(os.path.dirname(__file__), "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    f.save(os.path.join(upload_dir, fname))
    m.cover_photo_url = "/static/uploads/" + fname
    db.session.commit()
    return ok({"coverPhotoUrl": m.cover_photo_url})


@api.patch("/markets/<mid>")
@login_required
def market_update(mid):
    m = Market.query.get(mid)
    if not m:
        return fail("ไม่พบตลาด", 404)
    if session.get("role") != "ADMIN" and m.owner_id != session.get("user_id"):
        return fail("ไม่มีสิทธิ์", 403)
    d = request.get_json(silent=True) or {}
    if "name" in d and (d["name"] or "").strip():
        m.name = d["name"].strip()
    if "description" in d:
        m.description = (d["description"] or "").strip() or None
    if "openingHours" in d:
        m.opening_hours = (d["openingHours"] or "").strip() or None
    if "tags" in d:
        m.tags = (d["tags"] or "").strip() or None
    if "coverPhotoUrl" in d:
        import re as _re
        raw = (d["coverPhotoUrl"] or "").strip()
        m.cover_photo_url = raw if _re.match(r"^https?://", raw, _re.IGNORECASE) else None
    db.session.commit()
    return ok({"marketId": m.id})


@api.delete("/markets/<mid>")
@login_required
def market_delete(mid):
    m = Market.query.get(mid)
    if not m:
        return fail("ไม่พบตลาด", 404)
    if session.get("role") != "ADMIN" and m.owner_id != session.get("user_id"):
        return fail("ไม่มีสิทธิ์", 403)
    name_snap = m.name
    db.session.delete(m)
    Review.query.filter_by(target_type="MARKET", target_id=mid).delete()
    Favorite.query.filter_by(market_id=mid).delete()
    write_audit("DELETE_MARKET", "MARKET", mid, name_snap)
    db.session.commit()
    return ok({"deleted": True})


@api.get("/owner/markets")
@login_required
def owner_markets():
    ms = (Market.query.filter_by(owner_id=session["user_id"])
          .order_by(Market.created_at.desc()).all())
    mid_list = [m.id for m in ms]
    rating_map = compute_market_ratings(mid_list)
    out = []
    for m in ms:
        paid_rev = db.session.query(func.sum(Payment.amount)).join(
            Booking, Payment.booking_id == Booking.id
        ).join(Lot, Booking.lot_id == Lot.id).filter(
            Lot.market_id == m.id, Payment.status == "PAID"
        ).scalar() or 0
        avg, cnt = rating_map.get(m.id, (0.0, 0))
        out.append({
            "id": m.id, "name": m.name, "province": m.province,
            "district": m.district, "coverPhotoUrl": m.cover_photo_url,
            "totalLots": len(m.lots),
            "availableLots": sum(1 for l in m.lots if l.status == "AVAILABLE"),
            "bookedLots":    sum(1 for l in m.lots if any(b.status in ("PENDING","CONFIRMED") for b in l.bookings)),
            "totalBookings": sum(len(l.bookings) for l in m.lots),
            "revenue": paid_rev,
            "avgRating": avg, "reviewCount": cnt,
            "lots": [lot_dto(l) for l in sorted(m.lots, key=lambda x: x.code)],
        })
    return ok({"markets": out})


# ============ LOTS ============
@api.get("/lots/<lid>")
def lot_get(lid):
    l = Lot.query.get(lid)
    if not l:
        return fail("ไม่พบล็อก", 404)
    return ok({"lot": {**lot_dto(l), "marketId": l.market.id,
                       "marketName": l.market.name,
                       "deposit": deposit_for(l.price_per_day)}})


@api.post("/lots")
@login_required
def lot_create():
    d = request.get_json(silent=True) or {}
    m = Market.query.get(d.get("marketId"))
    if not m or (m.owner_id != session.get("user_id") and session.get("role") != "ADMIN"):
        return fail("ไม่มีสิทธิ์เพิ่มล็อกในตลาดนี้", 403)
    if not (d.get("code") or "").strip():
        return fail("กรุณากรอกเลขล็อก")
    if d.get("rentType") not in RENT_TYPES:
        return fail("ประเภทเช่าไม่ถูกต้อง")
    try:
        price = float(d["pricePerDay"])
        if price <= 0: raise ValueError
    except (KeyError, TypeError, ValueError):
        return fail("ราคาไม่ถูกต้อง")
    l = Lot(market_id=m.id, code=d["code"].strip(), price_per_day=price,
            rent_type=d["rentType"], note=(d.get("note") or "").strip() or None)
    db.session.add(l)
    db.session.commit()
    return ok({"lotId": l.id, "lot": lot_dto(l)})


@api.post("/lots/bulk")
@login_required
def lot_bulk_create():
    """สร้างล็อกหลายอันพร้อมกัน เช่น A1-A10"""
    d = request.get_json(silent=True) or {}
    m = Market.query.get(d.get("marketId"))
    if not m or (m.owner_id != session.get("user_id") and session.get("role") != "ADMIN"):
        return fail("ไม่มีสิทธิ์", 403)
    prefix = (d.get("prefix") or "").strip()
    try:
        start = int(d.get("start", 1))
        end   = int(d.get("end", 1))
        price = float(d["pricePerDay"])
        if price <= 0 or start > end or end - start > 99:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return fail("ข้อมูลไม่ถูกต้อง (prefix, start, end, pricePerDay)")
    if d.get("rentType") not in RENT_TYPES:
        return fail("ประเภทเช่าไม่ถูกต้อง")

    created = []
    for n in range(start, end + 1):
        code = f"{prefix}{n}"
        l = Lot(market_id=m.id, code=code, price_per_day=price,
                rent_type=d["rentType"], note=(d.get("note") or "").strip() or None)
        db.session.add(l)
        created.append(code)
    db.session.commit()
    return ok({"created": created, "count": len(created)})


@api.put("/lots/<lid>")
@login_required
def lot_update(lid):
    """แก้ไขรายละเอียดล็อก (ราคา, ชื่อ, ประเภท, หมายเหตุ)"""
    l = Lot.query.get(lid)
    if not l:
        return fail("ไม่พบล็อก", 404)
    if l.market.owner_id != session.get("user_id") and session.get("role") != "ADMIN":
        return fail("ไม่มีสิทธิ์", 403)
    d = request.get_json(silent=True) or {}
    if "code" in d and (d["code"] or "").strip():
        l.code = d["code"].strip()
    if "pricePerDay" in d:
        try:
            p = float(d["pricePerDay"])
            if p > 0: l.price_per_day = p
        except (TypeError, ValueError):
            return fail("ราคาไม่ถูกต้อง")
    if "rentType" in d:
        if d["rentType"] not in RENT_TYPES:
            return fail("ประเภทเช่าไม่ถูกต้อง")
        l.rent_type = d["rentType"]
    if "note" in d:
        l.note = (d["note"] or "").strip() or None
    db.session.commit()
    return ok({"lot": lot_dto(l)})


@api.patch("/lots/<lid>")
@login_required
def lot_toggle(lid):
    """สลับสถานะ AVAILABLE <-> CLOSED"""
    l = Lot.query.get(lid)
    if not l or (l.market.owner_id != session.get("user_id") and session.get("role") != "ADMIN"):
        return fail("ไม่มีสิทธิ์", 403)
    l.status = "AVAILABLE" if l.status == "CLOSED" else "CLOSED"
    db.session.commit()
    return ok({"status": l.status})


@api.delete("/lots/<lid>")
@login_required
def lot_delete(lid):
    l = Lot.query.get(lid)
    if not l or (l.market.owner_id != session.get("user_id") and session.get("role") != "ADMIN"):
        return fail("ไม่มีสิทธิ์", 403)
    db.session.delete(l)
    db.session.commit()
    return ok({"deleted": True})


# ============ BOOKINGS ============
@api.post("/bookings")
@login_required
def booking_create():
    d = request.get_json(silent=True) or {}
    l = Lot.query.get(d.get("lotId"))
    if not l:
        return fail("ไม่พบล็อก", 404)
    if l.status == "CLOSED":
        return fail("ล็อกนี้ปิดให้บริการชั่วคราว", 409)
    try:
        date_str = d.get("startDate") or d.get("date")
        start = datetime.fromisoformat(date_str)
    except (KeyError, TypeError, ValueError):
        return fail("กรุณาเลือกวันที่")
    try:
        end_str = d.get("endDate")
        end = datetime.fromisoformat(end_str) if end_str else start
    except (TypeError, ValueError):
        end = start
    if end < start:
        return fail("วันสิ้นสุดต้องไม่ก่อนวันเริ่มต้น")

    # ตรวจ overlap ต่อวัน: bookings ที่ซ้อนกับ [start, end] (coalesce ให้ single-day เป็น [date, date])
    overlap = Booking.query.filter(
        Booking.lot_id == l.id,
        Booking.status.in_(["PENDING", "CONFIRMED"]),
        Booking.date <= end,
        func.coalesce(Booking.end_date, Booking.date) >= start,
    ).first()
    if overlap:
        return fail("วันที่นี้มีการจองแล้ว กรุณาเลือกวันอื่น", 409)

    dep = deposit_for(l.price_per_day)
    b = Booking(lot_id=l.id, seller_id=session["user_id"], date=start,
                start_date=start, end_date=end if end != start else None,
                deposit_amount=dep)
    db.session.add(b)
    db.session.commit()
    return ok({"bookingId": b.id, "depositAmount": dep})


@api.get("/bookings")
@login_required
def bookings_mine():
    bs = (Booking.query
          .options(joinedload(Booking.lot).joinedload(Lot.market))
          .filter_by(seller_id=session["user_id"])
          .order_by(Booking.created_at.desc()).all())
    return ok({"bookings": [{
        "id": b.id, "date": b.date.isoformat(), "status": b.status,
        "paymentStatus": b.payment_status, "depositAmount": b.deposit_amount,
        "lotCode": b.lot.code, "marketName": b.lot.market.name,
        "marketId": b.lot.market.id, "createdAt": b.created_at.isoformat(),
    } for b in bs]})


@api.get("/bookings/<bid>")
@login_required
def booking_get(bid):
    b = Booking.query.get(bid)
    if not b or b.seller_id != session.get("user_id"):
        return fail("ไม่พบการจอง", 404)
    return ok({"booking": {
        "id": b.id, "date": b.date.isoformat(), "status": b.status,
        "paymentStatus": b.payment_status, "depositAmount": b.deposit_amount,
        "lotCode": b.lot.code, "pricePerDay": b.lot.price_per_day,
        "rentType": b.lot.rent_type,
        "marketName": b.lot.market.name, "marketId": b.lot.market.id,
        "sellerName": b.seller.name if b.seller else "—",
        "qrPayload": b.payment.qr_payload if b.payment else None,
        "createdAt": b.created_at.isoformat(),
    }})


# ============ PAYMENTS ============
@api.post("/payments/<bid>/promptpay")
@login_required
def payment_promptpay(bid):
    b = Booking.query.get(bid)
    if not b or b.seller_id != session.get("user_id"):
        return fail("ไม่พบการจอง", 404)
    payload = generate_payload(os.environ.get("PROMPTPAY_ID", "0812345678"),
                               b.deposit_amount)
    if not b.payment:
        db.session.add(Payment(booking_id=b.id, amount=b.deposit_amount,
                               method="PROMPTPAY", status="PENDING", qr_payload=payload))
    else:
        b.payment.qr_payload = payload
    db.session.commit()
    return ok({"qrPayload": payload, "amount": b.deposit_amount})


@api.get("/payments/<bid>/qr.png")
@login_required
def payment_qr(bid):
    b = Booking.query.get(bid)
    if not b or b.seller_id != session.get("user_id"):
        return fail("ไม่พบการจอง", 404)
    payload = generate_payload(os.environ.get("PROMPTPAY_ID", "0812345678"),
                               b.deposit_amount)
    img = qrcode.make(payload)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@api.post("/payments/<bid>/confirm")
@login_required
def payment_confirm(bid):
    b = Booking.query.get(bid)
    if not b or b.seller_id != session.get("user_id"):
        return fail("ไม่พบการจอง", 404)
    if b.payment_status == "PAID":
        return ok({"confirmed": True})   # idempotent
    ts = int(_utcnow().timestamp())
    if not b.payment:
        db.session.add(Payment(booking_id=b.id, amount=b.deposit_amount,
                               method="PROMPTPAY", status="PAID",
                               ref=f"MOCK-{ts}"))
    else:
        b.payment.status = "PAID"
        b.payment.ref = f"MOCK-{ts}"
    b.status, b.payment_status = "CONFIRMED", "PAID"
    # lot.status ไม่ถูก set เป็น BOOKED — availability ตรวจต่อวัน ไม่ใช่ global
    db.session.add(Notification(
        user_id=b.seller_id, type="BOOKING_CONFIRMED",
        title="จองสำเร็จ",
        body=f"จองล็อก {b.lot.code} ที่ {b.lot.market.name} เรียบร้อย",
        link=f"/bookings",
    ))
    db.session.commit()
    return ok({"confirmed": True})


# ============ PROFILE / REVIEWS ============
@api.post("/profile")
@login_required
def profile_update():
    d = request.get_json(silent=True) or {}
    u = current_user()
    if "name" in d and (d["name"] or "").strip():
        u.name = d["name"].strip()
    u.shop_name    = (d.get("shopName") or "").strip() or None
    u.product_type = (d.get("productType") or "").strip() or None
    u.bio          = (d.get("bio") or "").strip() or None
    if "email" in d:
        u.email = (d["email"] or "").strip() or None
    db.session.commit()
    return ok({"user": user_full(u)})


@api.get("/reviews")
def reviews_list():
    tt, tid = request.args.get("targetType"), request.args.get("targetId")
    if not tt or not tid:
        return fail("ต้องระบุ target")
    rs = (Review.query
          .filter_by(target_type=tt, target_id=tid, is_hidden=False)
          .order_by(Review.created_at.desc()).all())
    avg = sum(r.rating for r in rs) / len(rs) if rs else None
    dist = {i: sum(1 for r in rs if r.rating == i) for i in range(1, 6)}
    return ok({
        "average": round(avg, 1) if avg else None, "count": len(rs),
        "distribution": dist,
        "reviews": [{"id": r.id, "rating": r.rating, "comment": r.comment,
                     "fromName": r.from_user.name,
                     "createdAt": r.created_at.isoformat()} for r in rs],
    })


@api.get("/reviews/recent")
def reviews_recent():
    """รีวิวล่าสุดคะแนนสูงสำหรับ homepage"""
    rs = (Review.query
          .filter(Review.is_hidden == False, Review.rating >= 4)
          .order_by(Review.created_at.desc()).limit(6).all())
    out = []
    for r in rs:
        m = Market.query.get(r.target_id) if r.target_type == "MARKET" else None
        out.append({
            "id": r.id, "rating": r.rating, "comment": r.comment,
            "fromName": r.from_user.name,
            "targetType": r.target_type,
            "marketName": m.name if m else None,
            "marketId": m.id if m else None,
            "createdAt": r.created_at.isoformat(),
        })
    return ok({"reviews": out})


@api.post("/reviews")
@login_required
def review_create():
    d = request.get_json(silent=True) or {}
    if d.get("targetType") not in ("MARKET", "SELLER") or not d.get("targetId"):
        return fail("ข้อมูลไม่ครบ")
    rating = int(d.get("rating") or 0)
    if not 1 <= rating <= 5:
        return fail("กรุณาให้คะแนน 1-5")
    db.session.add(Review(
        from_user_id=session["user_id"], target_type=d["targetType"],
        target_id=d["targetId"], rating=rating,
        comment=(d.get("comment") or "").strip() or None,
    ))
    # อัปเดต avg_rating บน Market
    if d["targetType"] == "MARKET":
        db.session.flush()
        refresh_market_rating(d["targetId"])
    db.session.commit()
    return ok()


# ============ FAVORITES ============
@api.get("/favorites")
@login_required
def favorites_list():
    favs = (Favorite.query.filter_by(user_id=session["user_id"])
            .order_by(Favorite.created_at.desc()).all())
    ms = [f.market for f in favs if f.market]
    mid_list = [m.id for m in ms]
    rating_map = compute_market_ratings(mid_list)
    fav_ids = {m.id for m in ms}
    return ok({"markets": [market_item(m, rating_map, fav_ids) for m in ms]})


@api.post("/favorites/<market_id>")
@login_required
def favorite_add(market_id):
    m = Market.query.get(market_id)
    if not m:
        return fail("ไม่พบตลาด", 404)
    existing = Favorite.query.filter_by(user_id=session["user_id"], market_id=market_id).first()
    if not existing:
        db.session.add(Favorite(user_id=session["user_id"], market_id=market_id))
        db.session.commit()
    return ok({"isFav": True})


@api.delete("/favorites/<market_id>")
@login_required
def favorite_remove(market_id):
    Favorite.query.filter_by(user_id=session["user_id"], market_id=market_id).delete()
    db.session.commit()
    return ok({"isFav": False})


# ============ MESSAGES ============
def thread_id_for(a, b):
    return "__".join(sorted([a, b]))


@api.get("/messages")
@login_required
def messages_get():
    me_id = session["user_id"]
    tid   = request.args.get("threadId")
    since = request.args.get("since")   # ISO timestamp — incremental fetch

    if tid:
        if me_id not in tid.split("__"):
            return fail("ไม่มีสิทธิ์", 403)
        q = Message.query.filter_by(thread_id=tid).order_by(Message.created_at)
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace("Z", "+00:00").replace("+00:00", ""))
                q = q.filter(Message.created_at > since_dt)
            except ValueError:
                pass
        msgs = q.all()
        return ok({"messages": [{"id": m.id, "body": m.body, "imageUrl": m.image_url,
                                  "mine": m.from_user_id == me_id,
                                  "createdAt": m.created_at.isoformat()} for m in msgs]})

    # รายการห้องแชท
    all_msgs = (Message.query
                .filter((Message.from_user_id == me_id) | (Message.to_user_id == me_id))
                .order_by(Message.created_at.desc()).all())
    seen, threads = set(), []
    for m in all_msgs:
        if m.thread_id in seen:
            continue
        seen.add(m.thread_id)
        other = m.to_user if m.from_user_id == me_id else m.from_user
        # unread count
        unread = Message.query.filter_by(
            thread_id=m.thread_id, to_user_id=me_id
        ).count()   # simplified — actual unread tracking needs a read-receipt table
        threads.append({
            "threadId": m.thread_id, "otherId": other.id,
            "otherName": other.name, "lastBody": m.body,
            "lastAt": m.created_at.isoformat(),
        })
    return ok({"threads": threads})


@api.post("/messages")
@login_required
def message_send():
    d = request.get_json(silent=True) or {}
    me_id, to_id = session["user_id"], d.get("toUserId")
    body = (d.get("body") or "").strip()
    if not to_id or not body:
        return fail("ข้อมูลไม่ครบ")
    if len(body) > 2000:
        return fail("ข้อความยาวเกินไป")
    tid = thread_id_for(me_id, to_id)
    db.session.add(Message(thread_id=tid, from_user_id=me_id, to_user_id=to_id, body=body))
    db.session.add(Notification(user_id=to_id, type="MESSAGE", title="ข้อความใหม่",
                                body=body[:60], link=f"/chat/{me_id}"))
    db.session.commit()
    return ok({"threadId": tid})


@api.get("/users/<uid>")
@login_required
def user_public(uid):
    u = User.query.get(uid)
    if not u:
        return fail("ไม่พบผู้ใช้", 404)
    return ok({"user": {"id": u.id, "name": u.name, "role": u.role,
                        "shopName": u.shop_name, "isVerified": u.is_verified}})


# ============ NOTIFICATIONS ============
@api.get("/notifications")
@login_required
def notifications_list():
    ns = (Notification.query.filter_by(user_id=session["user_id"])
          .order_by(Notification.created_at.desc()).limit(50).all())
    unread = sum(1 for n in ns if not n.read)
    return ok({"unread": unread, "notifications": [
        {"id": n.id, "type": n.type, "title": n.title, "body": n.body,
         "link": n.link, "read": n.read,
         "createdAt": n.created_at.isoformat()} for n in ns]})


@api.post("/notifications")
@login_required
def notifications_read():
    Notification.query.filter_by(user_id=session["user_id"], read=False).update({"read": True})
    db.session.commit()
    return ok()


# ============ SETTINGS ============
@api.get("/settings")
@login_required
def settings_get():
    u = current_user()
    return ok({"user": user_full(u)})


# ============ ADMIN ============
@api.get("/admin/stats")
@admin_required
def admin_stats():
    paid = db.session.query(func.sum(Payment.amount)).filter_by(status="PAID").scalar() or 0
    total_lots = Lot.query.count()
    booked_lots = (db.session.query(func.count(func.distinct(Booking.lot_id)))
                   .filter(Booking.status == "CONFIRMED").scalar() or 0)
    recent = (Booking.query
              .options(joinedload(Booking.seller),
                       joinedload(Booking.lot).joinedload(Lot.market))
              .order_by(Booking.created_at.desc()).limit(10).all())
    return ok({
        "stats": {
            "sellers":   User.query.filter_by(role="SELLER").count(),
            "owners":    User.query.filter_by(role="MARKET_OWNER").count(),
            "markets":   Market.query.count(),
            "lots":      total_lots,
            "bookings":  Booking.query.count(),
            "confirmed": Booking.query.filter_by(status="CONFIRMED").count(),
            "revenue":   paid,
            "occupancy": round(booked_lots / total_lots * 100, 1) if total_lots else 0,
        },
        "recent": [{
            "id": b.id, "seller": b.seller.name,
            "market": b.lot.market.name, "lot": b.lot.code,
            "status": b.status, "amount": b.deposit_amount,
            "createdAt": b.created_at.isoformat(),
        } for b in recent],
    })


@api.get("/admin/stats/chart")
@admin_required
def admin_chart():
    """ข้อมูลกราฟย้อนหลัง N วัน"""
    days = min(int(request.args.get("days", 30)), 90)
    start = _utcnow() - timedelta(days=days)
    rows = (db.session.query(
        func.date(Booking.created_at).label("day"),
        func.count(Booking.id).label("bookings"),
        func.coalesce(func.sum(Payment.amount), 0).label("revenue"),
    ).outerjoin(Payment, Payment.booking_id == Booking.id)
     .filter(Booking.created_at >= start, Payment.status == "PAID")
     .group_by(func.date(Booking.created_at))
     .order_by(func.date(Booking.created_at)).all())
    return ok({"data": [{"day": str(r.day), "bookings": r.bookings,
                          "revenue": float(r.revenue)} for r in rows]})


@api.get("/admin/users")
@admin_required
def admin_users_list():
    role = request.args.get("role")
    q    = (request.args.get("q") or "").strip()
    query = User.query
    if role:
        query = query.filter_by(role=role)
    if q:
        query = query.filter((User.name.contains(q)) | (User.phone.contains(q)))
    us = query.order_by(User.created_at.desc()).all()
    return ok({"users": [{
        "id": u.id, "name": u.name, "phone": u.phone, "role": u.role,
        "isVerified": u.is_verified, "isSuspended": u.is_suspended,
        "markets": len(u.markets), "bookings": len(u.bookings),
        "createdAt": u.created_at.isoformat(),
    } for u in us]})


@api.post("/admin/users")
@admin_required
def admin_user_create():
    d = request.get_json(silent=True) or {}
    name, phone, role = (d.get("name") or "").strip(), (d.get("phone") or "").strip(), d.get("role")
    if len(name) < 2 or not valid_phone(phone) or role not in ("SELLER", "MARKET_OWNER"):
        return fail("ข้อมูลไม่ถูกต้อง")
    if User.query.filter_by(phone=phone).first():
        return fail("เบอร์นี้มีอยู่แล้ว", 409)
    u = User(name=name, phone=phone, role=role)
    db.session.add(u)
    write_audit("CREATE_USER", "USER", None, name, {"phone": phone, "role": role})
    db.session.commit()
    return ok({"id": u.id})


@api.patch("/admin/users/<uid>")
@admin_required
def admin_user_update(uid):
    u = User.query.get(uid)
    if not u:
        return fail("ไม่พบผู้ใช้", 404)
    d = request.get_json(silent=True) or {}
    if "isSuspended" in d:
        u.is_suspended = bool(d["isSuspended"])
        action = "SUSPEND_USER" if u.is_suspended else "UNSUSPEND_USER"
        write_audit(action, "USER", uid, u.name)
    if "isVerified" in d:
        u.is_verified = bool(d["isVerified"])
    db.session.commit()
    return ok({"user": user_full(u)})


@api.delete("/admin/users/<uid>")
@admin_required
def admin_user_delete(uid):
    u = User.query.get(uid)
    if not u:
        return fail("ไม่พบผู้ใช้", 404)
    name_snap = u.name
    for m in list(u.markets):
        db.session.delete(m)
    Booking.query.filter_by(seller_id=uid).delete()
    Review.query.filter_by(from_user_id=uid).delete()
    Message.query.filter((Message.from_user_id == uid) | (Message.to_user_id == uid)).delete()
    Notification.query.filter_by(user_id=uid).delete()
    Favorite.query.filter_by(user_id=uid).delete()
    OtpCode.query.filter_by(phone=u.phone).delete()
    write_audit("DELETE_USER", "USER", uid, name_snap)
    db.session.delete(u)
    db.session.commit()
    return ok({"deleted": True})


@api.get("/admin/markets")
@admin_required
def admin_markets_list():
    q = (request.args.get("q") or "").strip()
    query = Market.query
    if q:
        query = query.filter(Market.name.contains(q))
    ms = query.order_by(Market.created_at.desc()).all()
    mid_list = [m.id for m in ms]
    rating_map = compute_market_ratings(mid_list)
    return ok({"markets": [market_item(m, rating_map) for m in ms]})


@api.patch("/admin/markets/<mid>")
@admin_required
def admin_market_update(mid):
    m = Market.query.get(mid)
    if not m:
        return fail("ไม่พบตลาด", 404)
    d = request.get_json(silent=True) or {}
    if "isFeatured" in d:
        m.is_featured = bool(d["isFeatured"])
        write_audit("FEATURE_MARKET", "MARKET", mid, m.name, {"featured": m.is_featured})
    if "isVerified" in d:
        m.is_verified = bool(d["isVerified"])
        write_audit("VERIFY_MARKET", "MARKET", mid, m.name, {"verified": m.is_verified})
    db.session.commit()
    return ok({"marketId": m.id, "isVerified": m.is_verified, "isFeatured": m.is_featured})


@api.delete("/admin/reviews/<rid>")
@admin_required
def admin_review_hide(rid):
    r = Review.query.get(rid)
    if not r:
        return fail("ไม่พบรีวิว", 404)
    r.is_hidden = True
    refresh_market_rating(r.target_id)
    write_audit("DELETE_REVIEW", "REVIEW", rid, r.comment[:40] if r.comment else "")
    db.session.commit()
    return ok({"hidden": True})


@api.get("/admin/audit")
@admin_required
def admin_audit_list():
    page = request.args.get("page", 1, type=int)
    per  = 30
    rows = (AuditLog.query.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * per).limit(per).all())
    total = AuditLog.query.count()
    return ok({
        "total": total, "page": page, "perPage": per,
        "logs": [{
            "id": l.id, "actorRole": l.actor_role, "action": l.action,
            "targetType": l.target_type, "targetName": l.target_name,
            "meta": l.meta_dict(), "createdAt": l.created_at.isoformat(),
        } for l in rows],
    })


# ============ CSV EXPORTS ============
@api.get("/admin/export/users.csv")
@admin_required
def export_users_csv():
    write_audit("EXPORT_CSV", meta={"file": "users.csv"})
    db.session.commit()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "name", "phone", "role", "email", "isVerified", "isSuspended",
                "markets", "bookings", "createdAt"])
    for u in User.query.order_by(User.created_at.desc()).all():
        w.writerow([u.id, u.name, u.phone, u.role, u.email or "",
                    u.is_verified, u.is_suspended,
                    len(u.markets), len(u.bookings), u.created_at.isoformat()])
    buf.seek(0)
    return send_file(io.BytesIO(buf.getvalue().encode("utf-8-sig")),
                     mimetype="text/csv",
                     as_attachment=True,
                     download_name="smart_hawker_users.csv")


@api.get("/admin/export/bookings.csv")
@admin_required
def export_bookings_csv():
    write_audit("EXPORT_CSV", meta={"file": "bookings.csv"})
    db.session.commit()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "seller", "market", "lot", "date", "status",
                "paymentStatus", "deposit", "createdAt"])
    for b in (Booking.query
              .options(joinedload(Booking.seller),
                       joinedload(Booking.lot).joinedload(Lot.market))
              .order_by(Booking.created_at.desc()).all()):
        w.writerow([b.id, b.seller.name, b.lot.market.name, b.lot.code,
                    b.date.date(), b.status, b.payment_status,
                    b.deposit_amount, b.created_at.isoformat()])
    buf.seek(0)
    return send_file(io.BytesIO(buf.getvalue().encode("utf-8-sig")),
                     mimetype="text/csv",
                     as_attachment=True,
                     download_name="smart_hawker_bookings.csv")


# ============ IDENTITY / e-KYC ============
@api.post("/identity/start")
@login_required
def identity_start():
    import secrets
    from identity import start_verification
    uid = session["user_id"]
    u   = current_user()
    if getattr(u, "verification_status", "UNVERIFIED") == "VERIFIED":
        return fail("ยืนยันตัวตนแล้ว")
    # Generate cryptographic state nonce to prevent CSRF and auth-bypass
    state = secrets.token_urlsafe(24)
    session["kyc_state"] = state
    session["kyc_uid"]   = uid
    result = start_verification(uid, state)
    if not result.get("ok"):
        return fail(result.get("error", "เริ่มยืนยันตัวตนไม่ได้"))
    if hasattr(u, "verification_status"):
        u.verification_status = "PENDING"
        db.session.commit()
    return ok({"redirectUrl": result["redirect_url"], "provider": result.get("provider")})


@api.get("/identity/callback")
def identity_callback():
    """OAuth2 callback — GET only (OAuth2 callbacks are always GET).
    Requires active session with matching kyc_state nonce."""
    from flask import redirect as flask_redirect
    from identity import verify

    # Must be logged in
    user_id = session.get("user_id")
    if not user_id:
        return flask_redirect("/login?next=/profile")

    params = dict(request.args)

    # Pop state from session (prevents replay)
    expected_state = session.pop("kyc_state", None)
    expected_uid   = session.pop("kyc_uid",   None)

    # Verify state nonce and that the session user matches
    if not expected_state or params.get("state") != expected_state:
        return flask_redirect("/profile?kyc=error")
    if not expected_uid or user_id != expected_uid:
        return flask_redirect("/profile?kyc=error")

    result = verify(user_id, params)
    u = User.query.get(user_id)
    if not u:
        return flask_redirect("/profile?kyc=error")

    if not result.get("ok"):
        if hasattr(u, "verification_status"):
            u.verification_status = "REJECTED"
            db.session.commit()
        return flask_redirect("/profile?kyc=error")

    if hasattr(u, "verification_status"):
        u.verification_status = "VERIFIED"
        u.id_hash       = result.get("id_hash")
        u.verified_name = result.get("display_name")
        u.verified_at   = result.get("verified_at")
    write_audit("IDENTITY_VERIFIED", "USER", user_id, u.name, {"provider": result.get("provider")})
    db.session.commit()
    return flask_redirect("/profile?verified=1")


@api.patch("/admin/users/<uid>/identity")
@admin_required
def admin_override_identity(uid):
    u = User.query.get(uid)
    if not u:
        return fail("ไม่พบผู้ใช้", 404)
    if not hasattr(u, "verification_status"):
        return fail("ระบบยังไม่รองรับ e-KYC — รัน migration ก่อน")
    d      = request.get_json(silent=True) or {}
    status = d.get("status")
    if status not in ("UNVERIFIED", "VERIFIED", "REJECTED"):
        return fail("status ไม่ถูกต้อง (UNVERIFIED / VERIFIED / REJECTED)")
    u.verification_status = status
    if status == "VERIFIED" and not getattr(u, "verified_at", None):
        u.verified_at = _utcnow()
    write_audit("ADMIN_OVERRIDE_IDENTITY", "USER", uid, u.name, {"status": status})
    db.session.commit()
    return ok({"userId": uid, "verificationStatus": status})


# ============ PUBLIC STATS + LEDGER + ZONES ============

@api.get("/stats")
def public_stats():
    """สถิติหน้าแรก (ไม่ต้อง auth)"""
    from sqlalchemy import func as sqlfunc
    markets  = db.session.query(Market).count()
    avail    = (db.session.query(sqlfunc.count(Lot.id))
                .filter(Lot.status == "AVAILABLE").scalar() or 0)
    avg_row  = db.session.query(sqlfunc.avg(Market.avg_rating)).scalar()
    avg_rat  = round(avg_row or 0, 1)
    ledger_count = db.session.query(AllocationRecord).count()
    # ดัชนีความโปร่งใสรวม = ค่าเฉลี่ยทุกตลาด
    all_ids  = [r[0] for r in db.session.query(Market.id).all()]
    if all_ids:
        t_scores = [alloc_engine.compute_transparency_index(mid) for mid in all_ids[:20]]
        t_index  = round(sum(t_scores) / len(t_scores), 1)
    else:
        t_index = 50.0
    return ok({
        "markets":      markets,
        "availableLots": avail,
        "avgRating":    avg_rat,
        "ledgerCount":  ledger_count,
        "transparencyIndex": t_index,
    })


@api.get("/ledger")
def public_ledger():
    """Public allocation ledger — ไม่ต้อง auth, paginated, filterable"""
    page      = max(1, int(request.args.get("page", 1)))
    per_page  = min(500, int(request.args.get("perPage", 20)))
    market_id = request.args.get("marketId", "").strip()
    district  = request.args.get("district", "").strip()
    province  = request.args.get("province", "").strip()
    method    = request.args.get("method", "").strip()
    status_f  = request.args.get("status", "").strip()
    search    = request.args.get("q", "").strip()

    q = db.session.query(AllocationRecord)
    if market_id: q = q.filter(AllocationRecord.market_id == market_id)
    if district:  q = q.filter(AllocationRecord.district == district)
    if province:  q = q.filter(AllocationRecord.province == province)
    if method:    q = q.filter(AllocationRecord.method == method)
    if status_f:  q = q.filter(AllocationRecord.status == status_f)
    if search:    q = q.filter(AllocationRecord.ref_no.ilike(f"%{search}%"))

    total = q.count()
    rows  = (q.order_by(AllocationRecord.allocated_at.desc())
              .offset((page - 1) * per_page)
              .limit(per_page)
              .all())

    def row_dto(r):
        return {
            "id":          r.id,
            "refNo":       r.ref_no,
            "lotCode":     r.lot.code if r.lot else "—",
            "marketName":  r.market.name if r.market else "—",
            "district":    r.district or "—",
            "province":    r.province or "—",
            "sellerName":  r.seller.name if r.seller else "—",
            "method":      r.method,
            "score":       r.score,
            "reason":      r.reason or "",
            "status":      r.status,
            "allocatedAt": r.allocated_at.isoformat(),
        }

    return ok({
        "records":  [row_dto(r) for r in rows],
        "total":    total,
        "page":     page,
        "perPage":  per_page,
        "pages":    (total + per_page - 1) // per_page,
    })


@api.get("/ledger/export.csv")
def ledger_export_csv():
    """Export ledger เป็น CSV — สาธารณะ"""
    import io as _io
    import csv as _csv
    rows = (db.session.query(AllocationRecord)
            .order_by(AllocationRecord.allocated_at.desc())
            .limit(5000).all())
    buf = _io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["เลขอ้างอิง","ตลาด","เขต","จังหวัด","รหัสล็อก","ชื่อผู้ค้า","วิธีจัดสรร","คะแนน","เหตุผล","สถานะ","วันที่"])
    for r in rows:
        w.writerow([
            r.ref_no,
            r.market.name if r.market else "",
            r.district or "",
            r.province or "",
            r.lot.code if r.lot else "",
            r.seller.name if r.seller else "",
            r.method,
            r.score or "",
            r.reason or "",
            r.status,
            r.allocated_at.strftime("%Y-%m-%d %H:%M"),
        ])
    buf.seek(0)
    from flask import Response
    return Response(
        buf.getvalue().encode("utf-8-sig"),  # utf-8-sig = Excel รู้จัก BOM
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=smart-hawker-ledger.csv"}
    )


@api.post("/admin/allocate")
@admin_required
def admin_allocate():
    """Admin: รันการจัดสรร lot ด้วย Fair Engine"""
    d = request.get_json(force=True)
    lot_id     = d.get("lotId", "").strip()
    applicants = d.get("applicants", [])   # list of seller_id
    method     = d.get("method", "SCORING")  # SCORING | LOTTERY
    salt       = d.get("salt", "")

    if not lot_id: return fail("lotId required")
    if not applicants: return fail("applicants required")

    if method == "LOTTERY":
        records = alloc_engine.allocate_lottery(lot_id, applicants, public_salt=salt)
    else:
        records = alloc_engine.allocate_scoring(lot_id, applicants)

    return ok({
        "count":   len(records),
        "winner":  records[0].seller_id if records else None,
        "refNo":   records[0].ref_no if records else None,
    })


@api.get("/zones")
def public_zones():
    """ข้อมูล zoning/density สำหรับแผนที่"""
    zones = db.session.query(ZoneData).all()
    out = []
    for z in zones:
        m = z.market
        if not m: continue
        lots_total  = len(m.lots)
        ratio = lots_total / z.max_capacity if z.max_capacity > 0 else 0
        if ratio >= 0.9:   level = "RED"
        elif ratio >= 0.7: level = "YELLOW"
        else:              level = "GREEN"
        out.append({
            "marketId":       m.id,
            "marketName":     m.name,
            "lat":            m.lat,
            "lng":            m.lng,
            "sidewalkWidth":  z.sidewalk_width_m,
            "maxCapacity":    z.max_capacity,
            "currentLots":    lots_total,
            "complaints":     z.complaints_count,
            "traffyIssues":   z.traffy_issues,
            "densityLevel":   level,
            "note":           z.note or "",
        })
    return ok({"zones": out})


@api.get("/open-data/allocations")
def open_data_allocations():
    """Open Data API — ดาวน์โหลด JSON พร้อม metadata"""
    fmt = request.args.get("format", "json")
    rows = (db.session.query(AllocationRecord)
            .filter(AllocationRecord.status == "ALLOCATED")
            .order_by(AllocationRecord.allocated_at.desc())
            .limit(1000).all())
    data = [{
        "ref_no":       r.ref_no,
        "market":       r.market.name if r.market else None,
        "district":     r.district,
        "province":     r.province,
        "lot_code":     r.lot.code if r.lot else None,
        "method":       r.method,
        "score":        r.score,
        "status":       r.status,
        "allocated_at": r.allocated_at.isoformat(),
    } for r in rows]
    if fmt == "csv":
        return ledger_export_csv()
    return ok({
        "meta": {
            "source":  "Smart Hawker Open Data",
            "license": "CC BY 4.0",
            "generated_at": _utcnow().isoformat(),
            "total": len(data),
        },
        "data": data,
    })


# ============ GOV DASHBOARD ============

@api.get("/gov/summary")
def gov_summary():
    """District-level aggregation for government dashboard"""
    from datetime import timedelta

    markets   = Market.query.options(selectinload(Market.lots)).all()
    zones_map = {z.market_id: z for z in ZoneData.query.all()}
    alloc_recs = AllocationRecord.query.all()

    buckets: dict = {}
    for m in markets:
        dk = m.district or "ไม่ระบุเขต"
        if dk not in buckets:
            buckets[dk] = {
                "district": dk, "province": m.province or "",
                "markets": 0, "totalLots": 0, "availableLots": 0,
                "complaints": 0, "traffyIssues": 0,
                "sidewalkWidths": [], "densityCount": {"GREEN": 0, "YELLOW": 0, "RED": 0},
                "marketIds": [], "recs": [],
            }
        b = buckets[dk]
        b["markets"]       += 1
        b["totalLots"]     += len(m.lots)
        b["availableLots"] += sum(1 for l in m.lots if l.status == "AVAILABLE")
        b["marketIds"].append(m.id)
        z = zones_map.get(m.id)
        if z:
            b["complaints"]   += z.complaints_count or 0
            b["traffyIssues"] += z.traffy_issues or 0
            if z.sidewalk_width_m:
                b["sidewalkWidths"].append(z.sidewalk_width_m)
            ratio = len(m.lots) / z.max_capacity if z.max_capacity > 0 else 0
            level = "RED" if ratio >= 0.9 else "YELLOW" if ratio >= 0.7 else "GREEN"
            b["densityCount"][level] += 1

    for r in alloc_recs:
        dk = r.district or "ไม่ระบุเขต"
        if dk in buckets:
            buckets[dk]["recs"].append(r)

    result = []
    for dk, b in sorted(buckets.items()):
        recs  = b["recs"]
        n     = len(recs)
        has_z = 1 if any(mid in zones_map for mid in b["marketIds"]) else 0
        if n:
            n_reason  = sum(1 for r in recs if r.reason and r.reason.strip())
            n_scoring = sum(1 for r in recs if r.method == "SCORING")
            fairness  = round((n_reason / n) * 50 + (n_scoring / n) * 30 + has_z * 20, 1)
            mdist     = {}
            for r in recs:
                mdist[r.method] = mdist.get(r.method, 0) + 1
        else:
            fairness = has_z * 20
            mdist    = {}
        sw = b["sidewalkWidths"]
        occ = round((b["totalLots"] - b["availableLots"]) / b["totalLots"] * 100, 1) if b["totalLots"] else 0
        result.append({
            "district":        dk,
            "province":        b["province"],
            "markets":         b["markets"],
            "totalLots":       b["totalLots"],
            "availableLots":   b["availableLots"],
            "occupancyPct":    occ,
            "complaints":      b["complaints"],
            "traffyIssues":    b["traffyIssues"],
            "avgSidewalkM":    round(sum(sw) / len(sw), 1) if sw else None,
            "densityCount":    b["densityCount"],
            "allocationCount": n,
            "methodDist":      mdist,
            "fairnessIndex":   fairness,
        })

    # Allocation trend — last 30 days
    cutoff = _utcnow() - timedelta(days=30)
    trend_q = (
        db.session.query(
            func.date(AllocationRecord.allocated_at).label("day"),
            func.count(AllocationRecord.id).label("cnt"),
        )
        .filter(AllocationRecord.allocated_at >= cutoff)
        .group_by(func.date(AllocationRecord.allocated_at))
        .order_by(func.date(AllocationRecord.allocated_at))
        .all()
    )
    trend = [{"day": str(r.day), "count": r.cnt} for r in trend_q]

    # Per-market occupancy
    market_occ = []
    for m in sorted(markets, key=lambda x: -(len(x.lots))):
        avail = sum(1 for l in m.lots if l.status == "AVAILABLE")
        total = len(m.lots)
        pct   = round((total - avail) / total * 100, 1) if total else 0
        z     = zones_map.get(m.id)
        market_occ.append({
            "name":          m.name,
            "district":      m.district or "—",
            "totalLots":     total,
            "availableLots": avail,
            "occupancyPct":  pct,
            "densityLevel":  z.density_level if z else "GREEN",
        })

    return ok({
        "districts": result, "total": len(result),
        "trend": trend, "marketOcc": market_occ[:12],
    })


# ============ WALK-IN / INCLUSION ============

@api.post("/walkin/booking")
@login_required
def walkin_booking():
    """Walk-in: สร้างการจองแทนผู้ค้าที่มาที่หน้างาน"""
    if session.get("role") not in ("MARKET_OWNER", "ADMIN"):
        return fail("เฉพาะเจ้าของตลาดหรือแอดมิน", 403)

    d     = request.get_json(silent=True) or {}
    phone = (d.get("phone") or "").strip()
    name  = (d.get("name") or "").strip()

    if not valid_phone(phone):
        return fail("เบอร์โทรไม่ถูกต้อง (ตัวเลข 10 หลัก)")
    if len(name) < 2:
        return fail("กรุณากรอกชื่อผู้ค้า")

    seller = User.query.filter_by(phone=phone).first()
    created_new = False
    if not seller:
        seller = User(name=name, phone=phone, role="SELLER", bio="(ลงทะเบียน walk-in)")
        db.session.add(seller)
        db.session.flush()
        created_new = True

    lot = Lot.query.get(d.get("lotId"))
    if not lot:
        return fail("ไม่พบล็อก", 404)
    if session.get("role") == "MARKET_OWNER" and lot.market.owner_id != session["user_id"]:
        return fail("ไม่มีสิทธิ์จองล็อกในตลาดนี้", 403)
    if lot.status == "CLOSED":
        return fail("ล็อกนี้ปิดให้บริการชั่วคราว", 409)

    try:
        start   = datetime.fromisoformat(d.get("startDate") or d.get("date", ""))
        end_str = d.get("endDate")
        end     = datetime.fromisoformat(end_str) if end_str else start
    except (TypeError, ValueError):
        return fail("กรุณาเลือกวันที่")

    if end < start:
        return fail("วันสิ้นสุดต้องไม่ก่อนวันเริ่มต้น")

    overlap = Booking.query.filter(
        Booking.lot_id == lot.id,
        Booking.status.in_(["PENDING", "CONFIRMED"]),
        Booking.date <= end,
        func.coalesce(Booking.end_date, Booking.date) >= start,
    ).first()
    if overlap:
        return fail("วันที่นี้มีการจองแล้ว กรุณาเลือกวันอื่น", 409)

    dep = deposit_for(lot.price_per_day)
    b   = Booking(
        lot_id=lot.id, seller_id=seller.id,
        date=start, start_date=start,
        end_date=end if end != start else None,
        deposit_amount=dep,
        status="CONFIRMED",
        payment_status="PENDING",
    )
    db.session.add(b)
    db.session.flush()

    try:
        alloc_engine.record_booking_allocation(b)
    except Exception:
        pass

    db.session.add(Notification(
        user_id=seller.id, type="BOOKING_CONFIRMED",
        title="จองล็อกสำเร็จ (Walk-in)",
        body=f"จองล็อก {lot.code} ที่ {lot.market.name} โดยเจ้าหน้าที่",
        link="/bookings",
    ))
    write_audit("WALKIN_BOOKING", "BOOKING", b.id, seller.name, {
        "lot": lot.code, "market": lot.market.name, "new": created_new
    })
    db.session.commit()

    return ok({
        "bookingId":        b.id,
        "sellerId":         seller.id,
        "sellerName":       seller.name,
        "createdNewSeller": created_new,
        "lotCode":          lot.code,
        "marketName":       lot.market.name,
        "date":             start.date().isoformat(),
        "endDate":          end.date().isoformat() if end != start else None,
        "depositAmount":    dep,
        "printUrl":         f"/confirm/{b.id}/print",
    })


@api.get("/walkin/receipt/<bid>")
@login_required
def walkin_receipt(bid):
    """ใบเสร็จ — เข้าถึงได้โดยผู้ค้า เจ้าของตลาด หรือแอดมิน"""
    b = Booking.query.get(bid)
    if not b:
        return fail("ไม่พบการจอง", 404)
    role = session.get("role")
    uid  = session.get("user_id")
    is_seller = b.seller_id == uid
    is_owner  = b.lot.market.owner_id == uid
    if not (is_seller or is_owner or role == "ADMIN"):
        return fail("ไม่มีสิทธิ์", 403)
    start = b.start_date or b.date
    end   = b.end_date or start
    phone = b.seller.phone if b.seller else "—"
    if b.seller and not is_seller and role != "ADMIN":
        phone = phone[:3] + "****" + phone[-3:] if len(phone) >= 6 else "****"
    return ok({"booking": {
        "id":            b.id,
        "lotCode":       b.lot.code,
        "marketName":    b.lot.market.name,
        "marketId":      b.lot.market.id,
        "district":      b.lot.market.district or "—",
        "sellerName":    b.seller.name if b.seller else "—",
        "sellerPhone":   phone,
        "date":          start.isoformat(),
        "endDate":       end.isoformat() if end != start else None,
        "status":        b.status,
        "depositAmount": b.deposit_amount,
        "createdAt":     b.created_at.isoformat(),
    }})


# ============ TRAFFY FONDUE (P1.3) ============

@api.get("/traffy/near")
def traffy_near():
    """เรื่องร้องเรียน Traffy ใกล้จุดที่ระบุ"""
    import traffy as _traffy
    try:
        lat    = float(request.args.get("lat", 13.7563))
        lng    = float(request.args.get("lng", 100.5018))
        radius = float(request.args.get("radius", 0.3))
    except (TypeError, ValueError):
        return fail("lat/lng ไม่ถูกต้อง")
    radius = min(radius, 2.0)
    items  = _traffy.fetch_complaints_near(lat, lng, radius)
    return ok({"complaints": items, "total": len(items)})


@api.get("/traffy/all")
def traffy_all():
    """เรื่องร้องเรียน Traffy ทุกโซนตลาด (สำหรับแสดงบนแผนที่)"""
    import traffy as _traffy
    zones    = ZoneData.query.all()
    combined = []
    seen     = set()
    for z in zones:
        m = z.market
        if not m:
            continue
        items = _traffy.fetch_complaints_near(m.lat, m.lng, radius_km=0.3)
        for item in items:
            key = (round(item["lat"], 4), round(item["lng"], 4))
            if key not in seen:
                seen.add(key)
                item["marketName"] = m.name
                item["marketId"]   = m.id
                combined.append(item)
    return ok({"complaints": combined, "total": len(combined)})


# ============ WEATHER / RESILIENCE (P1.4) ============

@api.get("/weather/alerts")
def weather_alerts():
    """Resilience alerts — weather + PM2.5 (live or mock)"""
    import weather as _weather
    try:
        lat = float(request.args.get("lat", _weather.BKK_LAT))
        lng = float(request.args.get("lng", _weather.BKK_LNG))
    except (TypeError, ValueError):
        lat, lng = _weather.BKK_LAT, _weather.BKK_LNG
    return ok(_weather.get_alerts(lat, lng))


# ============ AI OPTIMIZER (P2.2) ============

@api.get("/optimizer/suggest")
def optimizer_suggest():
    """Greedy allocation optimizer — อธิบายได้ ไม่ใช่กล่องดำ"""
    markets   = Market.query.options(selectinload(Market.lots)).all()
    zones_map = {z.market_id: z for z in ZoneData.query.all()}
    alloc_recs = AllocationRecord.query.all()
    rec_by_market: dict = {}
    for r in alloc_recs:
        rec_by_market.setdefault(r.market_id, []).append(r)

    suggestions = []
    for m in markets:
        recs  = rec_by_market.get(m.id, [])
        z     = zones_map.get(m.id)
        lots  = len(m.lots)
        avail = sum(1 for l in m.lots if l.status == "AVAILABLE")
        occ   = (lots - avail) / lots if lots else 0

        # Fairness score for this market
        n_reason  = sum(1 for r in recs if r.reason and r.reason.strip())
        n_scoring = sum(1 for r in recs if r.method == "SCORING")
        n         = len(recs)
        has_zone  = 1 if z else 0
        fairness  = round((n_reason / n) * 50 + (n_scoring / n) * 30 + has_zone * 20, 1) if n else has_zone * 20

        complaints = z.complaints_count if z else 0
        sw_width   = z.sidewalk_width_m if z else 2.5

        # Generate suggestions (up to 2 per market)
        mkt_sugs = []

        if z and occ > 0.9:
            reduction = max(1, round(lots * 0.1))
            mkt_sugs.append({
                "type":   "REDUCE_LOTS",
                "market": m.name,
                "detail": f"ลดล็อก {reduction} อัน (จาก {lots} → {lots - reduction}) เพื่อลดความแออัด",
                "impact": {"congestion": -15, "fairness": +5, "revenue": -8},
                "reason": f"อัตราใช้ล็อก {round(occ*100)}% เกิน 90% + ทางเท้า {sw_width}m อาจไม่เพียงพอ",
                "priority": "HIGH",
            })

        if fairness < 50 and n > 0:
            mkt_sugs.append({
                "type":   "SWITCH_TO_SCORING",
                "market": m.name,
                "detail": f"เปลี่ยนวิธีจัดสรรเป็น SCORING (ดัชนีปัจจุบัน {fairness}/100)",
                "impact": {"congestion": 0, "fairness": +25, "revenue": 0},
                "reason": f"มีการจัดสรร {n} ครั้ง แต่ {n - n_scoring} ครั้งไม่ใช้ระบบ scoring",
                "priority": "MEDIUM",
            })

        if complaints >= 5:
            mkt_sugs.append({
                "type":   "TRAFFY_REVIEW",
                "market": m.name,
                "detail": f"บังคับรีวิว Traffy ทุก 30 วัน (ร้องเรียนสะสม {complaints} เรื่อง)",
                "impact": {"congestion": -5, "fairness": +10, "revenue": 0},
                "reason": f"เรื่องร้องเรียนสูง — ต้องติดตามประเมินใหม่",
                "priority": "HIGH",
            })

        if sw_width and sw_width < 1.8 and lots > 10:
            mkt_sugs.append({
                "type":   "REDUCE_FOR_SIDEWALK",
                "market": m.name,
                "detail": f"ลดล็อกลง 20% เพื่อเพิ่มพื้นที่ทางเท้าให้ ≥2m",
                "impact": {"congestion": -20, "fairness": +8, "revenue": -15},
                "reason": f"ทางเท้าเพียง {sw_width}m ต่ำกว่าเกณฑ์ กทม. (1.5m เหลือสำหรับคน)",
                "priority": "HIGH" if sw_width < 1.5 else "MEDIUM",
            })

        suggestions.extend(mkt_sugs[:2])

    # Sort by priority
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    suggestions.sort(key=lambda s: priority_order.get(s.get("priority", "LOW"), 2))

    return ok({
        "suggestions": suggestions[:10],
        "total":       len(suggestions),
        "generated":   _utcnow().isoformat(),
        "note":        "Greedy algorithm — สมดุล ความแออัด / รายได้ / ความเป็นธรรม",
    })


# ============ OPEN DATA (P2.3 expanded) ============

@api.get("/open-data/markets")
def open_data_markets():
    """Open Data — ตลาดทั้งหมด (CC BY 4.0)"""
    markets = Market.query.options(selectinload(Market.lots)).all()
    return ok({
        "meta": {
            "source": "Smart Hawker Open Data",
            "license": "CC BY 4.0",
            "generated_at": _utcnow().isoformat(),
            "total": len(markets),
        },
        "data": [{
            "id":           m.id,
            "name":         m.name,
            "province":     m.province,
            "district":     m.district,
            "lat":          m.lat,
            "lng":          m.lng,
            "total_lots":   len(m.lots),
            "avail_lots":   sum(1 for l in m.lots if l.status == "AVAILABLE"),
            "avg_rating":   m.avg_rating,
            "is_verified":  m.is_verified,
            "opening_hours": m.opening_hours,
            "tags":         m.tag_list(),
        } for m in markets],
    })


@api.get("/open-data/zones")
def open_data_zones():
    """Open Data — ข้อมูล zoning/density ทุกตลาด (CC BY 4.0)"""
    zones = ZoneData.query.all()
    return ok({
        "meta": {
            "source":  "Smart Hawker Open Data",
            "license": "CC BY 4.0",
            "generated_at": _utcnow().isoformat(),
            "total": len(zones),
        },
        "data": [{
            "market_id":       z.market_id,
            "market_name":     z.market.name if z.market else None,
            "district":        z.market.district if z.market else None,
            "lat":             z.market.lat if z.market else None,
            "lng":             z.market.lng if z.market else None,
            "sidewalk_width_m": z.sidewalk_width_m,
            "max_capacity":    z.max_capacity,
            "density_level":   z.density_level,
            "complaints_count": z.complaints_count,
            "traffy_issues":   z.traffy_issues,
            "note":            z.note,
            "updated_at":      z.updated_at.isoformat() if z.updated_at else None,
        } for z in zones],
    })
