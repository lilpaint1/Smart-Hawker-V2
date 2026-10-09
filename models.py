"""โครงสร้างฐานข้อมูล (11 ตาราง) ด้วย SQLAlchemy
หมายเหตุ: ใช้ String สำหรับ role/status + ตรวจค่าด้วย constants.py (กัน mismatch)
"""
import uuid
import json
from datetime import datetime, timezone
from extensions import db


def new_id():
    """สร้าง id แบบสุ่ม (hex uuid4 = 32 chars, ไม่มี dash)"""
    return uuid.uuid4().hex


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    id           = db.Column(db.String, primary_key=True, default=new_id)
    role         = db.Column(db.String, nullable=False)        # SELLER | MARKET_OWNER | ADMIN
    phone        = db.Column(db.String, unique=True, nullable=False, index=True)
    email        = db.Column(db.String)
    name         = db.Column(db.String, nullable=False)
    avatar_url   = db.Column(db.String)
    # โปรไฟล์ผู้ขาย
    shop_name    = db.Column(db.String)
    product_type = db.Column(db.String)
    bio          = db.Column(db.String)
    # สถานะบัญชี
    is_verified  = db.Column(db.Boolean, default=False)
    is_suspended = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=_utcnow)
    # e-KYC (PDPA-safe: ไม่เก็บเลขบัตรดิบ)
    verification_status = db.Column(db.String, default="UNVERIFIED")  # UNVERIFIED|PENDING|VERIFIED|REJECTED
    id_hash             = db.Column(db.String)    # SHA-256 HMAC one-way hash — detect duplicates only
    verified_name       = db.Column(db.String)    # ชื่อจริงจากผู้ให้บริการ KYC
    verified_at         = db.Column(db.DateTime)


class Market(db.Model):
    id              = db.Column(db.String, primary_key=True, default=new_id)
    owner_id        = db.Column(db.String, db.ForeignKey("user.id"), nullable=False, index=True)
    name            = db.Column(db.String, nullable=False)
    description     = db.Column(db.String)
    province        = db.Column(db.String, nullable=False, index=True)
    district        = db.Column(db.String)
    lat             = db.Column(db.Float, nullable=False)
    lng             = db.Column(db.Float, nullable=False)
    cover_photo_url = db.Column(db.String)
    opening_hours   = db.Column(db.String)          # เช่น "จ-ศ 06:00-14:00"
    tags            = db.Column(db.String)           # comma-separated เช่น "อาหาร,ผัก,ของสด"
    popularity      = db.Column(db.Integer, default=0, index=True)
    avg_rating      = db.Column(db.Float, default=0.0)  # denormalized
    review_count    = db.Column(db.Integer, default=0)  # denormalized
    is_verified     = db.Column(db.Boolean, default=False)
    is_featured     = db.Column(db.Boolean, default=False)
    owner_type      = db.Column(db.String, default="PRIVATE")  # GOV | PRIVATE
    gov_ref         = db.Column(db.String)                     # BMA registry reference code
    created_at      = db.Column(db.DateTime, default=_utcnow)
    owner           = db.relationship("User", backref="markets")
    lots            = db.relationship("Lot", backref="market", cascade="all, delete-orphan")

    def tag_list(self):
        return [t.strip() for t in (self.tags or "").split(",") if t.strip()]


class Lot(db.Model):
    id           = db.Column(db.String, primary_key=True, default=new_id)
    market_id    = db.Column(db.String, db.ForeignKey("market.id"), nullable=False, index=True)
    code         = db.Column(db.String, nullable=False)
    price_per_day = db.Column(db.Float, nullable=False)
    rent_type    = db.Column(db.String, nullable=False)   # DAILY | WEEKLY | MONTHLY
    status       = db.Column(db.String, default="AVAILABLE", index=True)
    note         = db.Column(db.String)
    bookings     = db.relationship("Booking", backref="lot", cascade="all, delete-orphan")


class Booking(db.Model):
    id             = db.Column(db.String, primary_key=True, default=new_id)
    lot_id         = db.Column(db.String, db.ForeignKey("lot.id"), nullable=False, index=True)
    seller_id      = db.Column(db.String, db.ForeignKey("user.id"), nullable=False, index=True)
    date           = db.Column(db.DateTime, nullable=False)   # วันเริ่มต้น (compat)
    start_date     = db.Column(db.DateTime)                   # start date (date-range)
    end_date       = db.Column(db.DateTime)                   # end date (date-range)
    status         = db.Column(db.String, default="PENDING", index=True)
    deposit_amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String, default="PENDING")
    created_at     = db.Column(db.DateTime, default=_utcnow, index=True)
    seller         = db.relationship("User", backref="bookings")
    payment        = db.relationship("Payment", backref="booking", uselist=False,
                                     cascade="all, delete-orphan")


class Payment(db.Model):
    id         = db.Column(db.String, primary_key=True, default=new_id)
    booking_id = db.Column(db.String, db.ForeignKey("booking.id"), unique=True, nullable=False)
    amount     = db.Column(db.Float, nullable=False)
    method     = db.Column(db.String)       # PROMPTPAY | CARD
    status     = db.Column(db.String, default="PENDING")
    ref        = db.Column(db.String)
    qr_payload = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=_utcnow)


class Review(db.Model):
    id           = db.Column(db.String, primary_key=True, default=new_id)
    from_user_id = db.Column(db.String, db.ForeignKey("user.id"), nullable=False, index=True)
    target_type  = db.Column(db.String, nullable=False)   # MARKET | SELLER
    target_id    = db.Column(db.String, nullable=False, index=True)
    rating       = db.Column(db.Integer, nullable=False)
    comment      = db.Column(db.String)
    is_hidden    = db.Column(db.Boolean, default=False)   # admin can hide abusive reviews
    created_at   = db.Column(db.DateTime, default=_utcnow)
    from_user    = db.relationship("User")


class Message(db.Model):
    id           = db.Column(db.String, primary_key=True, default=new_id)
    thread_id    = db.Column(db.String, nullable=False, index=True)
    from_user_id = db.Column(db.String, db.ForeignKey("user.id"), nullable=False)
    to_user_id   = db.Column(db.String, db.ForeignKey("user.id"), nullable=False, index=True)
    body         = db.Column(db.String, nullable=False)
    image_url    = db.Column(db.String)
    created_at   = db.Column(db.DateTime, default=_utcnow, index=True)
    from_user    = db.relationship("User", foreign_keys=[from_user_id])
    to_user      = db.relationship("User", foreign_keys=[to_user_id])


class Notification(db.Model):
    id         = db.Column(db.String, primary_key=True, default=new_id)
    user_id    = db.Column(db.String, db.ForeignKey("user.id"), nullable=False, index=True)
    type       = db.Column(db.String)
    title      = db.Column(db.String)
    body       = db.Column(db.String)
    link       = db.Column(db.String)    # deep link URL
    read       = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=_utcnow)


class OtpCode(db.Model):
    id         = db.Column(db.String, primary_key=True, default=new_id)
    phone      = db.Column(db.String, nullable=False, index=True)
    code_hash  = db.Column(db.String, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    consumed   = db.Column(db.Boolean, default=False)
    attempts   = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=_utcnow)


class Favorite(db.Model):
    """ผู้ใช้บุ๊กมาร์กตลาดที่ชื่นชอบ"""
    id         = db.Column(db.String, primary_key=True, default=new_id)
    user_id    = db.Column(db.String, db.ForeignKey("user.id"), nullable=False)
    market_id  = db.Column(db.String, db.ForeignKey("market.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow)
    __table_args__ = (db.UniqueConstraint("user_id", "market_id", name="uq_fav_user_market"),)
    market     = db.relationship("Market")


class AuditLog(db.Model):
    """บันทึกการกระทำสำคัญของ admin (immutable — ห้ามลบ)"""
    id          = db.Column(db.String, primary_key=True, default=new_id)
    actor_id    = db.Column(db.String, db.ForeignKey("user.id"), nullable=True)  # None = admin session
    actor_role  = db.Column(db.String)       # ADMIN | MARKET_OWNER | SELLER
    action      = db.Column(db.String, nullable=False, index=True)
    target_type = db.Column(db.String)       # USER | MARKET | LOT | REVIEW | BOOKING
    target_id   = db.Column(db.String)
    target_name = db.Column(db.String)       # snapshot ชื่อตอนที่ลบ
    meta        = db.Column(db.String)       # JSON string สำหรับ extra context
    created_at  = db.Column(db.DateTime, default=_utcnow, index=True)

    def meta_dict(self):
        try: return json.loads(self.meta or "{}")
        except: return {}


class AllocationRecord(db.Model):
    """บันทึกการจัดสรรล็อกทุกครั้ง — public audit ledger (ห้ามลบ)"""
    __tablename__ = "allocation_record"
    id           = db.Column(db.String, primary_key=True, default=new_id)
    ref_no       = db.Column(db.String, unique=True, nullable=False, index=True)
    lot_id       = db.Column(db.String, db.ForeignKey("lot.id"), nullable=False, index=True)
    market_id    = db.Column(db.String, db.ForeignKey("market.id"), nullable=False, index=True)
    seller_id    = db.Column(db.String, db.ForeignKey("user.id"), nullable=True, index=True)
    booking_id   = db.Column(db.String, db.ForeignKey("booking.id"), nullable=True)
    method       = db.Column(db.String, default="SCORING", index=True)  # SCORING | LOTTERY | MANUAL | AUTO_BOOKING
    score        = db.Column(db.Float)
    score_detail = db.Column(db.String)   # JSON: {"wait":5,"rotation":2,"quota":1}
    reason       = db.Column(db.String)   # ข้อความอธิบายอ่านออก
    lottery_seed = db.Column(db.String)   # ถ้า method=LOTTERY: seed สาธารณะ
    status       = db.Column(db.String, default="ALLOCATED", index=True)  # ALLOCATED | CANCELLED | EXPIRED
    district     = db.Column(db.String, index=True)   # snapshot ตอนจัดสรร
    province     = db.Column(db.String, index=True)
    allocated_at = db.Column(db.DateTime, default=_utcnow, index=True)

    lot    = db.relationship("Lot",     foreign_keys=[lot_id])
    market = db.relationship("Market",  foreign_keys=[market_id])
    seller = db.relationship("User",    foreign_keys=[seller_id])


class ZoneData(db.Model):
    """ข้อมูลความหนาแน่น/ความจุโซนต่อตลาด (rule-based zoning สำหรับแผนที่)"""
    __tablename__ = "zone_data"
    id               = db.Column(db.String, primary_key=True, default=new_id)
    market_id        = db.Column(db.String, db.ForeignKey("market.id"), unique=True, nullable=False, index=True)
    sidewalk_width_m = db.Column(db.Float, default=2.5)
    max_capacity     = db.Column(db.Integer, default=20)
    complaints_count = db.Column(db.Integer, default=0)
    traffy_issues    = db.Column(db.Integer, default=0)   # จำนวนเรื่อง Traffy Fondue ในรัศมี 200m
    density_level    = db.Column(db.String, default="GREEN")  # GREEN | YELLOW | RED (คำนวณจาก lots/max_capacity)
    note             = db.Column(db.String)
    updated_at       = db.Column(db.DateTime, default=_utcnow)

    market = db.relationship("Market", backref=db.backref("zone", uselist=False))
