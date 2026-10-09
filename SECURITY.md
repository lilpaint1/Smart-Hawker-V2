# Smart Hawker — Security Report (V4)

Generated: 2026-06-18 | Version: 4.0

---

## CRITICAL (P0) — Fixed in V4

### P0-A: Identity Auth-Bypass via Unauthenticated Callback
- **Status:** FIXED
- **File:** `api.py` — `identity_callback()`, `identity_start()`; `identity.py` — `start_verification()`
- **Severity:** Critical — anyone could forge a KYC-verified status for any account
- **Root cause:** The `identity_callback` endpoint accepted `user_id` from the query string/body, requiring no authentication. Any attacker could call `/api/identity/callback?user_id=<victim_id>&mock=1` to mark any account as KYC-verified.
- **Fix applied:**
  1. `identity_start()` now generates a cryptographic state nonce (`secrets.token_urlsafe(24)`) and stores it in `session["kyc_state"]` + `session["kyc_uid"]`.
  2. `start_verification()` receives the `state` nonce and embeds it in the redirect URL (not the `user_id`).
  3. `identity_callback()` is GET-only (OAuth2 callbacks are always GET). It reads `user_id` **only from `session["user_id"]`**, pops the `kyc_state`/`kyc_uid` from session (prevents replay), verifies the returned `state` matches, and checks the session user matches `kyc_uid`. Returns 403 / redirects to `/profile?kyc=error` on any failure.
- **Residual risk:** None for the mock provider. For ThaiID production, ensure `THAIID_REDIRECT_URI` is registered and cannot be redirected to an attacker-controlled domain.

### P0-B: Stored XSS via HTML Attribute Injection
- **Status:** FIXED
- **File:** `static/js/app.js` — `marketCardHTML()`
- **Severity:** Critical — attacker-controlled market name/ID/URL in attribute positions could break out of attribute context
- **Root cause:** `marketCardHTML()` used `esc()` (text-node escaping, does not escape `"`) inside HTML attribute values (`href`, `onclick`, `aria-label`, `data-fav`). This allowed `"` injection to break attribute context.
- **Fix applied:**
  1. All attribute-position values now use `escAttr()` (escapes `&`, `"`, `'`, `<`, `>`).
  2. Added `safeUrl(url)` which validates `https?://` prefix before using any URL in a `src` attribute.
  3. Local `/static/` paths are also allowed for cover images (used by seed data).
  4. `onclick="go('/market/${escAttr(m.id)}')"` — ID is now attribute-safe.

---

## HIGH (P1) — Fixed / Mitigated in V4

### P1-C: Popularity Write-on-GET (unauthenticated)
- **Status:** FIXED
- **File:** `api.py` — `market_detail()`
- **Issue:** Every GET to `/api/markets/<mid>` unconditionally incremented `m.popularity` and committed to DB. This allowed any script to artificially inflate popularity.
- **Fix:** Session-keyed dedup — `session["viewed_{mid}"]` is checked; popularity only increments once per session.

### P1-D: Admin `market_create` Owner Validation
- **Status:** FIXED
- **File:** `api.py` — `market_create()`
- **Issue:** ADMIN could pass any `ownerId` (including non-existent IDs) when creating a market.
- **Fix:** When role is ADMIN and `ownerId` is supplied, validates `User.query.get(ownerId)` exists and returns 404 if not.

### P1-E: Incomplete `_auto_migrate`
- **Status:** FIXED
- **File:** `app.py` — `_auto_migrate()`
- **Issue:** New columns added in V3/V4 were not covered, causing `AttributeError` on older databases.
- **Fix:** Added all missing columns: `booking.start_date`, `booking.end_date`, `market.cover_photo_url`, `market.is_featured`, `market.is_verified`, `review.is_hidden`, `notification.link`, `notification.read`.

### P1-F: Admin Rate Limit Bypass via Reverse Proxy
- **Status:** FIXED (MITIGATED)
- **File:** `app.py` — `create_app()`
- **Issue:** `request.remote_addr` returned the proxy IP (e.g., 127.0.0.1) when behind nginx/PythonAnywhere, effectively bypassing IP-based rate limiting for admin login.
- **Fix:** Added `ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)` so real client IP is forwarded.
- **Residual risk:** Requires correct nginx `proxy_set_header X-Forwarded-For` configuration on the server side.

### P1-G: Review Integrity (No Booking Verification)
- **Status:** RESIDUAL — not yet enforced at DB level
- **File:** `api.py` — `review_create()`
- **Recommendation:** Add check that reviewer has a CONFIRMED booking with the target before allowing a review. Also add unique constraint `(from_user_id, target_type, target_id)` to the Review model to prevent duplicate reviews.

---

## MEDIUM (P2) — Fixed in V4

### P2-H: Missing Security Headers
- **Status:** FIXED
- **File:** `app.py` — `set_security_headers()` after_request handler
- **Fix:** Added `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=(self)`. HSTS added when `SESSION_COOKIE_SECURE=1`.

### P2-I: Body-Size DoS / Missing MAX_CONTENT_LENGTH
- **Status:** FIXED
- **File:** `app.py` — `create_app()`
- **Fix:** `MAX_CONTENT_LENGTH` set to 4 MB by default, configurable via `MAX_CONTENT_LENGTH` env var.

### P2-J: OTP Rate Limit by IP
- **Status:** FIXED
- **File:** `api.py` — `otp_request()`; added `_otp_ip_times` dict
- **Fix:** IP-based rate limit: max 5 OTP requests per IP per 10 minutes. Returns HTTP 429 on exceeded limit.

### P2-K: SameSite Cookie / CSRF
- **Status:** FIXED
- **File:** `app.py`
- **Fix:** `SESSION_COOKIE_SAMESITE = "Lax"` and `SESSION_COOKIE_HTTPONLY = True` are now set unconditionally (not only when `SESSION_COOKIE_SECURE` is set).

### P2-L: Production Hygiene Warnings
- **Status:** FIXED
- **File:** `app.py`
- **Fix:** Startup warnings added for `SMS_PROVIDER=console`, `IDENTITY_PROVIDER=mock`, `ENABLE_QUICK_LOGIN=1` when `FLASK_ENV=production`.

---

## Dedicated Identity Hash Key (§3.2)

- **Status:** FIXED
- **File:** `identity.py` — `hash_id()`
- **Fix:** Now uses `IDENTITY_HASH_KEY` env var (falls back to `SECRET_KEY`). This separates the PDPA-sensitive identity hash key from the session signing key. Set `IDENTITY_HASH_KEY` to a random 32-byte hex in production (see `.env.example`).

---

## Residual Risks & Recommendations

1. **Review integrity** (P1-G): Enforce booking-based gating and unique constraint on reviews.
2. **CSRF tokens**: SameSite=Lax mitigates most CSRF, but for sensitive mutations consider adding explicit CSRF tokens.
3. **ThaiID `sub` preference**: Store the provider's opaque `sub` rather than hashing the national ID directly (see `identity.py` PDPA notes).
4. **File upload path traversal**: The `/api/markets/<mid>/cover` upload uses `uuid4().hex` as filename — safe. But validate that `static/uploads/` is not served with directory listing in production.
5. **Rate limiting persistence**: Current rate limits (`_admin_fail_times`, `_otp_ip_times`) are in-memory and reset on process restart. For production with multiple workers, use Redis-backed rate limiting.
6. **Content Security Policy**: No CSP header is set. Consider adding a strict CSP to mitigate any remaining XSS vectors.
