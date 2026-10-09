"""ตัวช่วยกลาง: รูปแบบ response เดียวกัน + auth + OTP + ตรวจข้อมูล (กัน mismatch/โค้ดซ้ำ)"""
import os
import re
import hmac
import hashlib
import random
import json
from functools import wraps
from datetime import datetime, timedelta, timezone
from flask import jsonify, session
from models import User


# ---------- response รูปแบบเดียวกันทุก API ----------
def ok(data=None, **kw):
    payload = {"ok": True}
    if data:
        payload.update(data)
    payload.update(kw)
    return jsonify(payload)


def fail(error, code=400):
    return jsonify({"ok": False, "error": error}), code


# ---------- auth ----------
def current_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return fail("กรุณาเข้าสู่ระบบ", 401)
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "ADMIN":
            return fail("เฉพาะผู้ดูแลระบบ", 403)
        return fn(*args, **kwargs)
    return wrapper


def owner_or_admin_required(fn):
    """ต้องเป็น MARKET_OWNER หรือ ADMIN"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") not in ("MARKET_OWNER", "ADMIN"):
            return fail("เฉพาะเจ้าของตลาดหรือแอดมิน", 403)
        return fn(*args, **kwargs)
    return wrapper


# ---------- OTP ----------
def gen_otp():
    return f"{random.randint(0, 999999):06d}"


def hash_otp(phone, code):
    secret = os.environ.get("SECRET_KEY", "dev-secret")
    return hmac.new(secret.encode(), f"{phone}:{code}".encode(),
                    hashlib.sha256).hexdigest()


def otp_expiry(minutes=5):
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=minutes)


# ---------- validation ----------
def valid_phone(phone):
    return bool(re.fullmatch(r"0\d{9}", (phone or "").strip()))


def deposit_for(price_per_day):
    return max(50, round(price_per_day * 0.2))


# ---------- audit log ----------
def write_audit(action, target_type=None, target_id=None, target_name=None, meta=None):
    """บันทึก audit log — เรียกก่อน db.session.commit() ที่มีอยู่แล้ว"""
    from models import AuditLog
    from extensions import db
    log = AuditLog(
        actor_id=session.get("user_id"),
        actor_role=session.get("role", "UNKNOWN"),
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        meta=json.dumps(meta) if meta and not isinstance(meta, str) else meta,
    )
    db.session.add(log)


# ---------- market rating (aggregate แบบ efficient) ----------
def compute_market_ratings(market_ids=None):
    """คืน dict {market_id: (avg_rating, review_count)} — หนึ่ง query สำหรับหลายตลาด"""
    from models import Review
    from extensions import db
    from sqlalchemy import func
    query = db.session.query(
        Review.target_id,
        func.avg(Review.rating).label("avg"),
        func.count(Review.id).label("cnt"),
    ).filter(Review.target_type == "MARKET", Review.is_hidden == False)
    if market_ids:
        query = query.filter(Review.target_id.in_(market_ids))
    rows = query.group_by(Review.target_id).all()
    return {r.target_id: (round(float(r.avg), 1), r.cnt) for r in rows}


def refresh_market_rating(market_id):
    """อัปเดต avg_rating + review_count บน Market row (เรียกหลังเขียน review ใหม่)"""
    from models import Market
    from extensions import db
    rd = compute_market_ratings([market_id])
    avg, cnt = rd.get(market_id, (0.0, 0))
    m = Market.query.get(market_id)
    if m:
        m.avg_rating = avg
        m.review_count = cnt
