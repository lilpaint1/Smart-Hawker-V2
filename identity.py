"""Identity verification (e-KYC) — provider abstraction.

IDENTITY_PROVIDER env (default: mock):
  mock    — instant demo verification, no external calls (safe for dev/staging)
  thaiid  — ThaiID / DGA e-KYC (ดู THAIID_INTEGRATION.md สำหรับวิธี implement จริง)

PDPA compliance:
  • ไม่เก็บเลขบัตรประชาชนดิบ — เก็บแค่ SHA-256 HMAC hash (detect duplicates เท่านั้น)
  • เก็บเฉพาะ: verification_status, verified_name, id_hash, verified_at
  • เลขบัตรดิบอยู่ใน memory ระหว่าง verify() call แล้วถูก discard ทันที
"""
import os
import hashlib
import hmac
from datetime import datetime, timezone


IDENTITY_PROVIDER = os.environ.get("IDENTITY_PROVIDER", "mock")


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_id(national_id_or_sub: str) -> str:
    """One-way HMAC-SHA256 of national ID / provider sub with IDENTITY_HASH_KEY salt.
    ใช้เพื่อ detect duplicate registrations เท่านั้น — ย้อนกลับไม่ได้
    Prefers IDENTITY_HASH_KEY over SECRET_KEY for dedicated separation."""
    key = os.environ.get("IDENTITY_HASH_KEY") or os.environ.get("SECRET_KEY", "dev-secret")
    return hmac.new(key.encode(), national_id_or_sub.encode(), hashlib.sha256).hexdigest()


def start_verification(user_id: str, state: str) -> dict:
    """เริ่มกระบวนการยืนยันตัวตน — คืน redirect_url ให้ผู้ใช้ไป consent
    state คือ cryptographic nonce จาก api.py (ไม่รับ user_id ใน callback URL)"""
    if IDENTITY_PROVIDER == "thaiid":
        return _thaiid_start(user_id, state)
    # mock: ส่ง URL callback ทดสอบทันที — ไม่มี user_id ใน URL
    return {
        "ok": True,
        "provider": "mock",
        "redirect_url": f"/api/identity/callback?state={state}&mock=1",
        "state": state,
    }


def verify(user_id: str, params: dict) -> dict:
    """ประมวลผล callback จาก provider — คืนข้อมูลผู้ใช้ที่ยืนยันแล้ว
    state ถูกตรวจใน api.py ก่อนเรียกฟังก์ชันนี้แล้ว"""
    if IDENTITY_PROVIDER == "thaiid":
        return _thaiid_callback(user_id, params)
    # mock: สร้างข้อมูลจำลองทันที (state verified by api.py already)
    mock_name = params.get("mock_name", "นาย ทดสอบ ระบบ")
    # Use provider sub instead of raw national ID when available
    mock_sub = params.get("sub", params.get("mock_id", "mock-sub-0000"))
    return {
        "ok":           True,
        "provider":     "mock",
        "display_name": mock_name,
        "id_hash":      hash_id(mock_sub),
        "verified_at":  _utcnow(),
    }


# ---- ThaiID / DGA seam (implement when going live) ----

def _thaiid_start(user_id: str, state: str) -> dict:
    """OAuth2 authorization redirect ไปยัง DGA consent page.

    Real flow:
    1. POST to THAIID_AUTH_URL with client_id, redirect_uri (THAIID_REDIRECT_URI), state=nonce
    2. Return consent URL for user redirect
    3. User consents → DGA redirects back to /api/identity/callback?code=...&state=...
    4. Exchange code for token at THAIID_TOKEN_URL
    5. Fetch userinfo from THAIID_USERINFO_URL
    6. Extract verified name + encrypted national ID / sub

    Required env:
      THAIID_CLIENT_ID, THAIID_CLIENT_SECRET
      THAIID_AUTH_URL, THAIID_TOKEN_URL, THAIID_USERINFO_URL
      THAIID_REDIRECT_URI

    Note: state is a cryptographic nonce (not user_id) — stored in Flask session by api.py
    """
    client_id = os.environ.get("THAIID_CLIENT_ID")
    auth_url  = os.environ.get("THAIID_AUTH_URL")
    redirect  = os.environ.get("THAIID_REDIRECT_URI")
    if not (client_id and auth_url and redirect):
        return {"ok": False,
                "error": "ThaiID env ไม่ครบ — ตั้ง THAIID_CLIENT_ID, THAIID_AUTH_URL, THAIID_REDIRECT_URI (ดู THAIID_INTEGRATION.md)"}
    import urllib.parse
    url_params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id":     client_id,
        "redirect_uri":  redirect,
        "scope":         "openid profile national_id",
        "state":         state,
    })
    return {"ok": True, "provider": "thaiid", "redirect_url": f"{auth_url}?{url_params}", "state": state}


def _thaiid_callback(user_id: str, params: dict) -> dict:
    """แลก authorization code เป็น token แล้วดึง userinfo."""
    code          = params.get("code")
    client_id     = os.environ.get("THAIID_CLIENT_ID")
    client_secret = os.environ.get("THAIID_CLIENT_SECRET")
    token_url     = os.environ.get("THAIID_TOKEN_URL")
    userinfo_url  = os.environ.get("THAIID_USERINFO_URL")
    redirect      = os.environ.get("THAIID_REDIRECT_URI")
    if not all([code, client_id, client_secret, token_url, userinfo_url, redirect]):
        return {"ok": False,
                "error": "ThaiID callback env ไม่ครบ หรือไม่มี code — ดู THAIID_INTEGRATION.md"}
    # TODO: implement token exchange + userinfo fetch
    # ดูตัวอย่างใน THAIID_INTEGRATION.md §4
    return {"ok": False, "error": "ThaiID callback ยังไม่ implement — ดู THAIID_INTEGRATION.md §4"}
