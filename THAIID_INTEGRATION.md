# ThaiID / DGA e-KYC Integration Guide

Smart Hawker ใช้ระบบ e-KYC เพื่อยืนยันตัวตนผู้ใช้ผ่าน provider abstraction (`identity.py`).
ค่าเริ่มต้นเป็น `mock` provider สำหรับ dev/staging — ไม่มี external call.

---

## 1. ภาพรวม ThaiID / DGA

**ThaiID** คือบริการยืนยันตัวตนอิเล็กทรอนิกส์ของ DGA (สำนักงานพัฒนารัฐบาลดิจิทัล)
โดยใช้ **NDID** (National Digital ID Platform) เป็น infrastructure กลาง.

ผู้ใช้ยืนยันตัวตนด้วยบัตรประชาชน + facial recognition ผ่านแอป banking partner
(กสิกร, SCB, ไทยพาณิชย์ ฯลฯ) — Smart Hawker ไม่แตะบัตรดิบเลย.

---

## 2. OAuth2 / OIDC Flow

```
User browser          Smart Hawker          DGA OAuth2 Server
     |                     |                      |
     |-- POST /identity/start -->                  |
     |                     |-- redirect_url -----→ |
     |<-- 302 redirect to consent page            |
     |                     |                      |
     |--- user consents on DGA page -----------→  |
     |                     |                      |
     |<--- 302 callback to /api/identity/callback?code=...&state=...
     |                     |                      |
     |          POST token exchange ------------→  |
     |                     |<-- access_token ----  |
     |          GET /userinfo ----------------→   |
     |                     |<-- { name, sub, ... } |
     |                     |                      |
     |<-- profile verified |                      |
```

---

## 3. Environment Variables ที่ต้องตั้ง

```bash
IDENTITY_PROVIDER=thaiid

THAIID_CLIENT_ID=your-client-id           # จาก DGA developer portal
THAIID_CLIENT_SECRET=your-client-secret
THAIID_AUTH_URL=https://imauth.bora.dopa.go.th/api/oauth2/auth
THAIID_TOKEN_URL=https://imauth.bora.dopa.go.th/api/oauth2/token
THAIID_USERINFO_URL=https://imauth.bora.dopa.go.th/api/oauth2/userinfo
THAIID_REDIRECT_URI=https://yourdomain.com/api/identity/callback
```

---

## 4. Implementation Steps (ใน `identity.py`)

### 4.1 `_thaiid_start()` — สร้าง authorization URL

```python
import urllib.parse, secrets

state = secrets.token_urlsafe(16)  # CSRF protection
# store state in session: session["kyc_state"] = state

params = urllib.parse.urlencode({
    "response_type": "code",
    "client_id":     client_id,
    "redirect_uri":  redirect,
    "scope":         "openid profile national_id",
    "state":         state,
})
return {"ok": True, "redirect_url": f"{auth_url}?{params}"}
```

### 4.2 `_thaiid_callback()` — แลก code เป็น token

```python
import urllib.request, base64, json

# Verify state matches session (CSRF check)

# Exchange code for token
data = urllib.parse.urlencode({
    "grant_type":   "authorization_code",
    "code":         code,
    "redirect_uri": redirect_uri,
}).encode()
auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
req  = urllib.request.Request(token_url, data=data, headers={
    "Authorization": f"Basic {auth}",
    "Content-Type":  "application/x-www-form-urlencoded",
})
with urllib.request.urlopen(req, timeout=15) as r:
    token_data = json.loads(r.read())

access_token = token_data["access_token"]

# Fetch userinfo
req2 = urllib.request.Request(userinfo_url, headers={
    "Authorization": f"Bearer {access_token}"
})
with urllib.request.urlopen(req2, timeout=15) as r:
    userinfo = json.loads(r.read())

# Extract data — field names depend on DGA scope
national_id  = userinfo.get("national_id") or userinfo.get("sub")
display_name = userinfo.get("name") or userinfo.get("given_name", "") + " " + userinfo.get("family_name", "")

return {
    "ok":           True,
    "display_name": display_name.strip(),
    "id_hash":      hash_id(national_id),  # one-way hash — never store raw
    "verified_at":  _utcnow(),
}
```

---

## 5. PDPA Compliance

| ข้อมูล | เก็บหรือไม่ | เหตุผล |
|--------|-------------|--------|
| เลขบัตรประชาชน | **ไม่เก็บ** | PDPA sensitive data — ไม่จำเป็น |
| HMAC-SHA256 hash ของเลขบัตร | เก็บใน `user.id_hash` | ตรวจ duplicate เท่านั้น ย้อนกลับไม่ได้ |
| ชื่อจากผู้ให้บริการ KYC | เก็บใน `user.verified_name` | แสดงผล verified badge |
| เวลาที่ยืนยัน | เก็บใน `user.verified_at` | audit trail |
| ข้อมูลอื่นจาก userinfo | **ไม่เก็บ** | minimize data collection |

**การจัดการข้อมูล**: ข้อมูลยืนยันตัวตนเป็น sensitive personal data ตาม PDPA.
ต้องแจ้งนโยบายความเป็นส่วนตัว (Privacy Policy) ให้ชัดเจนก่อนให้ผู้ใช้ consent.

---

## 6. State / Nonce Flow (V4 Security Fix)

V4 แก้ไข auth-bypass vulnerability ด้วยการเพิ่ม cryptographic state nonce:

```
1. POST /api/identity/start  (requires login session)
   → api.py: state = secrets.token_urlsafe(24)
   → session["kyc_state"] = state
   → session["kyc_uid"]   = session["user_id"]
   → identity.start_verification(uid, state)
      → redirect URL: /api/identity/callback?state={state}&...

2. User redirected to DGA consent page (state embedded in URL)

3. DGA redirects back: GET /api/identity/callback?code=...&state={state}

4. api.identity_callback():
   - user_id = session.get("user_id")      ← ONLY from session, never from request
   - expected_state = session.pop("kyc_state")   ← pops to prevent replay
   - expected_uid   = session.pop("kyc_uid")
   - VERIFY: params["state"] == expected_state   ← CSRF / auth-bypass protection
   - VERIFY: user_id == expected_uid             ← user can only verify own account
   - On failure: redirect /profile?kyc=error     ← no info leak
   - On success: verify(user_id, params)         ← state already checked
```

**Why this matters**: Without the nonce, an attacker could forge a callback URL and mark any account as verified. The nonce ties the callback to a specific session and user.

---

## 7. Sub / PDPA Model (V4)

V4 prefers storing the provider's opaque `sub` claim rather than hashing the raw national ID:

| Approach | Pros | Cons |
|----------|------|------|
| `hash_id(national_id)` | Detect duplicate registrations | national_id is PDPA sensitive; if key leaked, all hashes vulnerable |
| `hash_id(sub)` — **V4 default** | sub is opaque (provider-controlled), no PDPA national_id handling | Sub may change if user re-authorizes |

For production, use `IDENTITY_HASH_KEY` (separate from `SECRET_KEY`) to further isolate the hashing key:

```bash
# .env — generate with: python -c "import secrets; print(secrets.token_hex(32))"
IDENTITY_HASH_KEY=<random-32-bytes-hex>
```

The `id_hash` column is never returned to clients (confirmed: `user_full()` in `api.py` does not include `id_hash`).

---

## 8. Sandbox / Testing

DGA มี sandbox environment สำหรับทดสอบก่อน go-live:
- ลงทะเบียน developer account ที่ DGA Developer Portal
- ใช้ test national ID: `1234567890123` (sandbox only)
- ระบบปัจจุบันใช้ `IDENTITY_PROVIDER=mock` ซึ่งข้ามขั้นตอนทั้งหมด

---

## 9. References

- DGA Developer Portal: https://developer.dga.or.th
- NDID Official: https://www.ndid.co.th
- PDPA Thailand: https://www.pdpa.pro
