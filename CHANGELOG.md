# Changelog — Smart Hawker

All notable changes are listed by file. Dates are YYYY-MM-DD.

---

## 2026-06-18 — V7: Auth State Visibility + Logout

### Changes
| File | Change |
|------|--------|
| `static/js/app.js` | Added global `logout()` — `POST /auth/logout` then redirect `/`; replaces per-page copies |
| `templates/_sidenav.html` | Sidebar footer replaced: **logged in** shows account card (avatar, name, role label) + settings + logout button; **logged out** shows prominent "เข้าสู่ระบบ" / "สมัครสมาชิก" buttons on desktop, icon links on tablet icon-rail |
| `templates/_bottomnav.html` | Seller/guest "โปรไฟล์" tab replaced with "เข้าสู่ระบบ" tab when `not me` — prevents misleading tab label for unauthenticated mobile users |
| `templates/_appheader.html` | Added auth affordance in header: avatar pill → `/profile` when logged in; "เข้าสู่ระบบ" button when guest |
| `templates/profile.html` | `render()` wrapped in try/catch — shows "โหลดโปรไฟล์ไม่สำเร็จ / ลองใหม่" card instead of blank skeleton on error; removed duplicate local `logout()` (now uses global) |
| `static/css/styles.css` | Added `.sidebar-account-card`, `.sidebar-account-avatar`, `.sidebar-account-info`, `.sidebar-auth-btns`, `.sidebar-link-tablet`, `.sidebar-logout`, `.header-avatar` — with tablet-breakpoint overrides |

---

## 2026-06-18 — V6: Bug Fixes + Full Click-Every-Button QA

### Per-route status after QA pass
| Route | Status |
|-------|--------|
| `/` | ✅ Hero, launcher cards, featured markets, stats all render |
| `/login` | ✅ OTP flow, resend timer, Quick Login, register link on unknown-phone error |
| `/register` | ✅ Form, quick-register unchanged |
| `/search` | ✅ Filter, market cards, map link |
| `/map` | ✅ All 4 layer buttons, popups, weather banner, Traffy markers |
| `/transparency` | ✅ Ledger loads, filters, search, pagination, Export CSV, QR modal |
| `/transparency/how-it-works` | ✅ Formula, examples, กทม. block |
| `/simulator` | ✅ Sliders recompute, radar chart, compare table |
| `/gov` | ✅ KPIs, 4 charts, district table, Transparency Ranking, AI Optimizer |
| `/owner` | ✅ (no change) |
| `/admin`, `/admin/*` | ✅ (no change) |

### Bugs found → root cause → fix

| # | Bug | Root cause | Fix |
|---|-----|------------|-----|
| 1 | Two sidebar items highlighted simultaneously (e.g. `/transparency` + `/transparency/how-it-works` both active) | `setActiveSidebarLink()` used `path.startsWith(href)` — parent `/transparency` matched child path | Replaced with most-specific-match: only the link with the longest matching `href` gets `.active`; parent only activates on exact match or `href + "/"` prefix |
| 2 | `/map` appeared twice in sidebar — once in "ความโปร่งใส", once in seller "ค้นหา" section | Duplicate `<a href="/map">` in `_sidenav.html` added in V5 | Removed the duplicate from the seller/guest "ค้นหา" block; `/map` remains in "ความโปร่งใส" for all roles |
| 3 | `GET /api/weather/alerts` → 500 `ValueError: 'MODERATE' is not in list` | `_MOCK_AQI["level"]` was `"MODERATE"` (AirNow category) but `get_alerts()` expected one of `["GREEN","YELLOW","RED"]`; `levels.index("MODERATE")` crashed | Fixed mock to `"GREEN"` (AQI 95 → GREEN in our thresholds); added defensive normalization: unknown level strings fall back to `_classify_aqi(aqi_val)` |
| 4 | Resend OTP button showed no loading state when clicked | `requestOtp(isResend=true)` hardcoded `btn = $("#btn-otp")` (the hidden step-1 button) instead of the visible `#btn-resend` | Changed to `const btn = isResend ? $("#btn-resend") : $("#btn-otp")` |
| 5 | "ไม่พบเบอร์นี้" error on login left user with no clear path to register | Error was shown as plain text; the existing register link below the form is easy to miss | When error contains "ไม่พบ", inject inline `<a href="/register">สมัครสมาชิก →</a>` directly into the error element |
| 6 | Province filter dropdown in `/transparency` could miss provinces from records after position 50 | `GET /api/ledger` had `per_page = min(50, ...)` cap; `loadProvinceFilter` requested `perPage=1000` but got capped at 50 | Raised cap to `min(500, ...)` — sufficient for production without excessive DB load |

### Files changed
- **`static/js/app.js`** — `setActiveSidebarLink()` rewritten with most-specific-match algorithm
- **`templates/_sidenav.html`** — removed duplicate `/map` link from seller "ค้นหา" section
- **`templates/login.html`** — resend button loading fix; "ไม่พบเบอร์" error adds inline register link
- **`api.py`** — `public_ledger()` per_page cap raised from 50 → 500
- **`weather.py`** — `_MOCK_AQI["level"]` corrected to `"GREEN"`; added defensive level normalization in `get_alerts()`

---

## 2026-06-18 — V5: 3-Tier Responsive + Civic-Tech Nav + Rebrand + GOV Seed

### Responsive test matrix

| Viewport | Device class | Layout               | Result |
|----------|--------------|----------------------|--------|
| 375px    | Phone        | Bottom-nav, no sidebar | ✓ |
| 768px    | iPad Mini    | Icon-rail sidebar (72px), no bottom-nav | ✓ |
| 834px    | iPad Air     | Icon-rail sidebar (72px) | ✓ |
| 1024px   | iPad Pro / small laptop | Full sidebar (248px) | ✓ |
| 1280px   | Desktop      | Full sidebar (248px) | ✓ |

### static/css/styles.css
- Added 3-tier responsive shell: Phone (<768px bottom-nav), Tablet (768–1023px icon-rail 72px sidebar), Desktop (≥1024px full sidebar 248px)
- Added `img, svg, video, canvas { max-width:100% }` + `* { min-width:0 }` global overflow safety
- Tablet breakpoint: sidebar width 72px, brand name + link text + section headers hidden, icons only with `title` tooltip
- Added `.table-scroll` utility: `overflow-x:auto; -webkit-overflow-scrolling:touch`
- Added `.sim-layout` collapse to single column on `max-width:1023px`
- Added `.hide-tablet` utility class

### templates/_sidenav.html
- Brand icon: replaced inline SVG with `<img src=".../img/logo.svg">` (34×34)
- Added "ความโปร่งใส" section visible to all roles (transparency, how-it-works, map, simulator, gov dashboard)
- All 5 civic-tech links have `title=` and `aria-label=` for tablet icon-rail accessibility
- "เจ้าของตลาด" → "จัดการพื้นที่", "ตลาดของฉัน" → "พื้นที่ของฉัน"

### templates/_bottomnav.html
- Complete rewrite: max 5 items across all roles
- Added `#more-sheet` slide-up bottom sheet containing all 5 transparency/civic-tech links
- "เพิ่มเติม" button (more-horizontal icon) opens sheet; backdrop dismisses it
- Role-specific bottom tabs: Seller (search, map, bookings?, profile, โปร่งใส) | Owner (พื้นที่, แชท, แจ้งเตือน, โปรไฟล์, เพิ่มเติม) | Admin (แดชบอร์ด, พื้นที่, ผู้ใช้, เพิ่มเติม)

### templates/login.html + register.html
- Replaced inline store icon with `<img src=".../img/logo.svg">` (52×52)

### static/favicon.svg
- Replaced old store icon with market-stall awning design (pink gradient badge + white awning)

### static/manifest.webmanifest
- name: "Smart Hawker — เปิดพื้นที่ค้าขาย"
- description rebrand; shortcuts: ค้นหาพื้นที่ + ตรวจสอบความโปร่งใส
- icons: logo.svg (purpose:any) + favicon.svg (purpose:maskable)

### constants.py
- Added `OWNER_TYPES = ["GOV", "PRIVATE"]` + `OWNER_TYPE_LABEL` dict
- Added strings: owner, space, spaces, add_space, manage_space
- Exported `OWNER_TYPES` + `OWNER_TYPE_LABEL` to `CLIENT_CONFIG` → `window.CONFIG`

### models.py
- `Market`: added `owner_type` (String, default "PRIVATE") + `gov_ref` (String, nullable)

### app.py
- `_auto_migrate()`: added `ALTER TABLE market ADD COLUMN owner_type` + `gov_ref`

### api.py
- `market_item()`: added `ownerType` + `govRef` fields
- Added `GET /api/open-data/markets` + `GET /api/open-data/zones` (CC BY 4.0)
- Added `GET /api/traffy/near` + `GET /api/traffy/all` (mock-first, live via `TRAFFY_PROVIDER=live`)
- Added `GET /api/weather/alerts` (mock-first, live via `OPENWEATHER_KEY`)
- Added `GET /api/optimizer/suggest` (Greedy AI, 4 suggestion types, priority-sorted)

### static/js/app.js
- `marketCardHTML()`: added GOV badge (blue chip with landmark icon) + "พื้นที่ผ่านการรับรอง" label

### templates/index.html
- **§3 Hero**: "เปิดพื้นที่ให้ค้าขาย" H1 + value prop + 3 pillars (โปร่งใส · เป็นธรรม · ไม่ทิ้งใคร)
- **§7 Logo**: logo.svg (56×56) in hero + footer
- **§2.3 Launcher**: "สำรวจระบบ" section with 6 tappable cards (transparency, how-it-works, map, simulator, gov, search) in auto-fill grid
- "ตลาดแนะนำ" → "พื้นที่แนะนำ"; hero badge updated; search placeholder updated

### templates/gov.html
- **§4 Integration**: "การเชื่อมต่อกับ กทม." card with 3 labeled panels (Open Data = Live, Traffy = Mock, BMA gov_ref = Demo-ready)
- Added AI Optimizer card, Transparency Ranking card
- `.table-scroll` on district table

### templates/transparency_how.html
- **§4 Integration**: "เชื่อมต่อกับ กทม." block with 3 labeled integration points

### templates/transparency.html
- Added QR Audit column (11th column, colspan updated everywhere)
- Added QR modal + `showQr()` / `closeQr()`
- Wrapped table in `.table-scroll`

### templates/simulator.html
- Added Before/After radar chart (Chart.js 4)
- Module-level `BASE` object updated from live `/api/gov/summary`
- `loadBaseline()` async function; compare table header shows live label

### templates/map.html
- Added Traffy Fondue layer (purple/red/yellow/gray markers by complaint type)
- Added weather alert banner (GREEN/YELLOW/RED)

### seed_demo.py
- Added "พื้นที่ค้าขายสวนลุมพินี" as GOV (gov_ref: BMA-LUM-2024-001)
- "ตลาดอตก." → GOV (gov_ref: BMA-JJK-2023-007)
- All other markets → PRIVATE
- Summary shows GOV/PRIVATE counts

---

## 2026-06-18 — V4: Security Hardening + Blossom Theme + Market Images

### api.py
- **P0-A SECURITY FIX**: `identity_callback()` — removed unauthenticated POST handler; GET-only OAuth2 callback now validates cryptographic state nonce from session; `user_id` never accepted from request params
- **P0-A SECURITY FIX**: `identity_start()` — generates `secrets.token_urlsafe(24)` state nonce; stores `kyc_state` + `kyc_uid` in session
- **P0-B SECURITY FIX**: `marketCardHTML()` — all HTML attribute values now use `escAttr()`; added `safeUrl()` for cover image URLs
- **P1-C**: `market_detail()` popularity increment now session-keyed to prevent inflate-on-refresh
- **P1-D**: `market_create()` validates `ownerId` exists in DB when ADMIN supplies it
- **P2-J**: `otp_request()` now has IP-based rate limit (5 per IP per 10 min) via `_otp_ip_times`
- Added `POST /api/markets/<mid>/cover` file upload endpoint (validates image MIME + extension)
- `market_item()` now includes `ownerVerified` field (owner `verification_status == "VERIFIED"`)
- `markets_list()` now uses `selectinload(Market.lots)` + `joinedload(Market.owner)` to fix N+1
- `market_create()` / `market_update()`: validate `coverPhotoUrl` allows `https?://` only
- Added `selectinload`, `secrets` imports

### identity.py
- `hash_id()` renamed param to `national_id_or_sub`; now uses `IDENTITY_HASH_KEY` env (falls back to `SECRET_KEY`)
- `start_verification(user_id, state)` — added `state` parameter; mock redirect URL no longer includes `user_id`
- `verify()` — state verification removed (now handled by `api.py`); uses `sub` over raw mock_id
- `_thaiid_start(user_id, state)` — updated to pass `state` nonce (not `user_id`) to provider

### app.py
- **P1-E**: `_auto_migrate()` extended with all missing columns (booking.start_date, booking.end_date, market.cover_photo_url, market.is_featured, market.is_verified, review.is_hidden, notification.link, notification.read)
- **P1-F**: Added `ProxyFix` middleware for correct client IP behind reverse proxy
- **P2-H**: Added `set_security_headers()` after_request handler (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, HSTS)
- **P2-I**: `MAX_CONTENT_LENGTH` now set unconditionally (default 4 MB)
- **P2-K**: `SESSION_COOKIE_SAMESITE="Lax"` and `SESSION_COOKIE_HTTPONLY=True` set unconditionally
- **P2-L**: Startup warnings for SMS_PROVIDER=console, IDENTITY_PROVIDER=mock, ENABLE_QUICK_LOGIN=1 in production

### static/js/theme.js
- Added `blossom` accent (`h:345, s:68%`) to ACCENTS
- Changed `DEFAULT_ACCENT` from `"amber"` to `"blossom"`

### constants.py
- Added `"blossom": {"h": 345, "s": "68%", ...}` to `ACCENT_THEMES`

### static/css/styles.css
- Updated `:root` light theme tokens to Blossom palette (pink-tinted bg/ink/line)
- Updated `:root` `--brand-h/s/l` defaults to blossom (345, 68%, 56%)
- Updated `[data-theme="dark"]` to deep plum tones (hsl 340-based)
- Added `.market-card .cover-overlay` gradient for image readability

### static/js/app.js
- Added `safeUrl(url)` function (https?:// validation)
- `marketCardHTML()` — all attribute values use `escAttr()`, cover image uses `safeUrl()`/local path check
- Added `ownerVerified` badge rendering in compact and full card modes
- Changed `AVA[0]` from amber `#d97706` to rose `#e06090`
- Changed star rating colors from hard-coded amber hex to CSS `var(--warn)`

### templates/base.html
- Updated `theme-color` meta from `#d97706` to `#e06090`

### static/manifest.webmanifest
- Updated `theme_color` to `#e06090`, `background_color` to `#1a0a10`

### static/favicon.svg
- Updated fill colors from amber/orange to rose `#e06090` / `#b83070`

### templates/owner.html
- Added "รูปหน้าปกตลาด (URL)" form field (`#m-cover`)
- `addMarket()` payload now includes `coverPhotoUrl: safeUrl(rawCover)`
- `delLot()` and `confirmDelMarket()` now use themed `confirmDialog()` instead of native `confirm()`

### static/img/markets/ (new directory)
- Added 6 colorful SVG placeholder images: `food.svg`, `fresh.svg`, `clothes.svg`, `night.svg`, `general.svg`, `craft.svg`

### seed.py
- Added `cover_photo_url` and `tags` to all seed markets (pointing to local SVG files)
- Added 6th market (ตลาดงานฝีมือ สีลม)

### .env.example
- Added `IDENTITY_HASH_KEY=` entry with description

### SECURITY.md (new)
- Created comprehensive security report covering P0/P1/P2 findings, fixes, and residual risks

---

## 2026-06-18 — Production Redesign (v2.0)

### pythonanywhere_wsgi.py
- **FIXED** critical SyntaxError: `os.environ["ADMIN_CODE"] = ` had no value on line 16 → crashed server boot
- Replaced with `os.environ.setdefault()` for safe non-secret defaults only
- Added startup warning log if SECRET_KEY or ADMIN_CODE are unset
- SECRET_KEY and ADMIN_CODE must come from actual environment (no fallbacks)

### constants.py
- Added `LOT_STATUS`, `NOTIFICATION_TYPES`, `AUDIT_ACTIONS`, `ROLE_LABEL_SHORT`
- Added `BOOKING_STATUS_LABEL`, `PAYMENT_STATUS_LABEL`, `LOT_STATUS_LABEL`, `BOOKING_STATUS_COLOR`
- Added `ACCENT_THEMES` dict with 6 HSL hue variants (amber/teal/indigo/rose/violet/emerald)
- Added `STRINGS` dict for i18n TH/EN string table (~30 keys)
- Extended `CLIENT_CONFIG` to include all new dicts (STRINGS, ACCENT_THEMES, colors, etc.)

### models.py
- Added DB indexes on all frequently-queried columns (phone, market_id, lot_id, status, created_at, etc.)
- `User`: added `is_verified`, `is_suspended` columns
- `Market`: added `opening_hours`, `tags`, `avg_rating` (denormalized), `review_count` (denormalized), `is_verified`, `is_featured`; added `tag_list()` helper method
- `Booking`: added `start_date`, `end_date` for date-range bookings (old `date` column kept for backward compat)
- `Review`: added `is_hidden` for admin content moderation
- `Notification`: added `link` column for deep links from notification cards
- **NEW** `Favorite(id, user_id, market_id, created_at)` — wishlist with UniqueConstraint
- **NEW** `AuditLog(id, actor_id, actor_role, action, target_type, target_id, target_name, meta[JSON], created_at)` — immutable admin action log

### helpers.py
- Added `owner_or_admin_required` decorator
- Added `write_audit(action, target_type, target_id, target_name, meta)` — inserts AuditLog row (caller must commit)
- Added `compute_market_ratings(market_ids)` — single GROUP BY query, returns `{market_id: (avg, count)}`
- Added `refresh_market_rating(market_id)` — updates denormalized `avg_rating` + `review_count` on Market row

### api.py (complete rewrite — 26+ endpoints)
- **SECURITY**: `admin_login()` removes hardcoded `"ake112233"` fallback → returns 503 if `ADMIN_CODE` env unset
- `market_item()`: includes `coverPhotoUrl`, `tags`, `avgRating`, `reviewCount`, `isVerified`, `isFeatured`, `isFav`
- `markets_list()`: added `sort` (popularity/rating/price), `minPrice`, `available=1`, `limit` params
- **NEW** `GET /api/markets/featured` — top 8 featured markets for homepage
- **NEW** `PATCH /api/markets/<mid>` — edit name/description/openingHours/tags/coverPhotoUrl
- `market_delete()`: also cleans up Favorites, writes AuditLog
- `owner_markets()`: returns `revenue` (sum of paid payments), `avg_rating` per market
- **NEW** `POST /api/lots/bulk` — bulk create lots (prefix + numeric range + price + rent type)
- **NEW** `PUT /api/lots/<lid>` — full lot edit (code, pricePerDay, rentType, note)
- `lot_toggle()`: blocks toggling BOOKED lots (returns 409)
- `booking_create()`: overlap prevention query, supports `startDate`/`endDate` range bookings
- `payment_confirm()`: idempotent — checks `payment_status == "PAID"` before processing (double-tap safe)
- `reviews_list()`: filters `is_hidden=False`, returns `distribution` dict (per-star counts)
- **NEW** `GET /api/reviews/recent` — latest 6 high-rated reviews for homepage
- `review_create()`: calls `refresh_market_rating()` after creating review
- **NEW** `GET /api/favorites` — list user's favorite markets
- **NEW** `POST /api/favorites/<market_id>` — add favorite
- **NEW** `DELETE /api/favorites/<market_id>` — remove favorite
- `messages_get()`: supports `since=` ISO timestamp for incremental polling
- **NEW** `DELETE /api/me` — self account deletion
- `admin_users_list()`: supports `role` filter + `q` text search
- `admin_user_create()`: writes AuditLog on creation
- **NEW** `PATCH /api/admin/users/<uid>` — suspend/verify user, writes AuditLog
- `admin_user_delete()`: writes AuditLog on deletion
- **NEW** `GET /api/admin/markets` — market list with rating data and owner info
- **NEW** `PATCH /api/admin/markets/<mid>` — verify/feature market, writes AuditLog
- **NEW** `DELETE /api/admin/reviews/<rid>` — hide review, refresh rating, write AuditLog
- **NEW** `GET /api/admin/audit` — paginated AuditLog viewer (supports `q`, `page`, `per_page`)
- **NEW** `GET /api/admin/stats/chart?days=N` — daily bookings + revenue for SVG chart
- **NEW** `GET /api/admin/export/users.csv` — CSV export of all users
- **NEW** `GET /api/admin/export/bookings.csv` — CSV export of all bookings
- **NEW** `GET /api/settings` — returns current user theme settings

### app.py
- Added startup logging with warnings for missing SECRET_KEY and ADMIN_CODE
- Automatic `postgres://` → `postgresql://` URL rewrite for SQLAlchemy 2.x compat
- `SESSION_COOKIE_SECURE`, `HTTPONLY`, `SAMESITE` read from env
- Context processor: added `current_path` (request.path), `default_theme`, `default_lang`
- `/search` and `/market/<mid>` now public (no `@page_login_required`)
- **NEW** routes: `/settings`, `/favorites`, `/admin/markets`, `/admin/audit`
- **NEW** error handlers: 404 → `templates/errors/404.html`, 500 → `templates/errors/500.html`

### static/js/theme.js (NEW)
- FOUC prevention: runs synchronously in `<head>` before CSS link
- Reads `localStorage` / cookie → sets `data-theme`, `--brand-h`, `--brand-s`, `data-accent`, `data-senior`, `lang` on `<html>` before first paint
- Exposes `window.THEME` API: `set()`, `setAccent()`, `setSenior()`, `setLang()`, `toggle()`, `current()`, `currentAccent()`, `currentLang()`, `isSenior()`, `accentList`, `accents`

### static/css/styles.css (complete rewrite ~550 lines)
- Full HSL-based CSS custom property design token system
- Dark theme via `[data-theme="dark"]`
- Senior mode via `[data-senior="1"]` — scales font 18px base
- 6-accent hue system via `--brand-h` + `--brand-s`
- **REMOVED** `.app-frame { max-width: 480px }` phone lock
- Responsive app shell: `.app-shell`, `.sidebar` (desktop only ≥1024px), `.content-wrap`, `.bottomnav` (mobile only)
- WCAG 2.2 AA focus-visible outlines, prefers-reduced-motion support
- `.otp-cells` + `.otp-cell` (6 individual inputs)
- `.search-layout` 3-column (filters | results | map) desktop layout
- `.stat-card`, `.lot-row`, `.accent-swatch` components
- SVG chart styles, `.admin-table`, `.role-card`, toast system, shimmer animation

### static/js/app.js (major extension)
- Full API client with 12s timeout, AbortController, auto-retry for GETs
- `t(key)` i18n helper using `C.STRINGS`
- `marketCardHTML(m, compact)` — complete market card HTML
- `skelCards(n, cls)` — skeleton loading placeholder HTML
- `toggleFav(marketId, btn)` — fav/unfav with Toast feedback
- `stars(n, size)` — star rating HTML
- `setBtnLoading()` — spinner + disable on submit
- `debounce()`, `avaColor()`, `avatarEl()`, `thb()`, `fmtDate()`, `fmtTime()`
- PWA service worker registration
- `setActiveSidebarLink()` — highlights active nav based on `location.pathname`
- Bell badge auto-refresh every 10s

### templates/base.html
- `theme.js` in `<head>` (synchronous, before CSS) for FOUC prevention
- Google Fonts preconnect (IBM Plex Sans Thai + Sarabun)
- `.app-shell` replaces `.app-frame`
- `{% block sidebar %}{% include "_sidenav.html" %}{% endblock %}`
- `#toast-root` div added
- PWA `<link rel="manifest">` and `<link rel="icon">` added

### templates/_sidenav.html (NEW)
- Role-aware sidebar navigation (ADMIN / MARKET_OWNER / SELLER + guest)
- `current_path` for active link highlighting
- Bell badge inline within nav items
- Settings + theme toggle in sidebar footer

### templates/_bottomnav.html
- Role-aware: SELLER/guest / MARKET_OWNER / ADMIN layouts
- `aria-label`, `aria-current` on all links

### templates/_quicklogin.html
- **FIXED** swapped labels: "ผู้ขาย" and "เจ้าของตลาด" were reversed
- Uses `Toast.error()` instead of `alert()`

### templates/index.html (redesign)
- Separated from `/login` — homepage is now public
- Hero section with value prop, search bar (→/search), live stats
- Featured markets grid (via `GET /api/markets/featured`)
- "How it works" 3-step section
- Recent reviews carousel (via `GET /api/reviews/recent`)
- CTA section with gradient
- Footer with theme toggle

### templates/login.html
- No sidebar on auth pages (`{% block sidebar %}{% endblock %}`)
- 6-cell OTP inputs (auto-advance, paste support, Enter key)
- 60s resend timer with `setInterval`
- `setBtnLoading()` on all submit buttons

### templates/register.html
- No sidebar on auth pages
- Role cards as ARIA `radiogroup` with `role-card.selected` class
- Fixed role labels matching constants.py

### templates/search.html (major update)
- Desktop 3-col layout: filter aside | results | Leaflet map
- Mobile: horizontal chip rows for province + rent type
- Leaflet.markercluster for pin clustering
- debounce 280ms on search input
- Map toggle button for mobile full-screen overlay

### templates/market.html (major update)
- Cover image or gradient placeholder
- Fav + Share buttons in topbar
- Mini Leaflet map (no controls)
- Rating distribution bars (5→1 star)
- Lot list with status chips and Book CTA
- Reviews section with star picker and write-review form
- Web Share API / clipboard fallback

### templates/book.html (rewrite)
- Date range picker (start + end date)
- Live price/deposit calculation
- Overlap check via API
- `setBtnLoading()` on submit

### templates/checkout.html (rewrite)
- PromptPay QR image + fallback placeholder
- 30-minute countdown timer
- Idempotency: redirects immediately if booking already paid

### templates/confirm.html (rewrite)
- Booking receipt with full date range, days count, deposit
- Links to bookings list and search

### templates/bookings.html (rewrite)
- Status tabs (all/pending/confirmed/cancelled)
- Action buttons: pay (pending), chat owner (confirmed)

### templates/chat.html (rewrite)
- Unread badge count per thread
- Avatar with deterministic color

### templates/chat_thread.html (rewrite)
- Incremental polling via `?since=<timestamp>` (only new messages)
- Optimistic send with rollback on failure
- Pause polling on hidden tab, resume on visibility

### templates/profile.html (rewrite)
- Avatar with dynamic color, verified badge
- Inline shop info edit for SELLER
- Links to settings, favorites, notifications

### templates/notifications.html (rewrite)
- Mark-all-read button
- Deep links from notification items
- Unread indicator per notification

### templates/owner.html (rewrite)
- KPI cards: markets, total lots, bookings, revenue
- Bulk lot creation form (prefix + range A1-A10)
- Inline lot editing (edit button opens form in-place)
- Nominatim reverse geocode for auto-fill province/district

### templates/admin.html (rewrite)
- KPI stat cards
- SVG time-series chart (daily bookings, 7/30 day toggle)
- Links to users, markets, audit log management pages
- CSV export links

### templates/admin_users.html (rewrite)
- Search + role filter toolbar
- Suspend/verify toggle per user
- Visual role chips and status badges

### templates/admin_login.html (polish)
- No sidebar on admin auth page
- `setBtnLoading()` on submit

### templates/admin_markets.html (NEW)
- Market table with verified/featured toggles
- Search + filter by verification status

### templates/admin_audit.html (NEW)
- Paginated AuditLog viewer
- Color-coded by action type
- Meta data display

### templates/settings.html (NEW)
- Theme picker (light/dark)
- Accent color swatches (6 options)
- Senior mode toggle
- Language selector (TH/EN)
- Account deletion with double-confirm

### templates/favorites.html (NEW)
- Saved markets grid using `marketCardHTML()`
- Empty state with search CTA

### templates/errors/404.html (NEW)
- Friendly 404 with navigation links

### templates/errors/500.html (NEW)
- Friendly 500 with reload button

### static/manifest.webmanifest (NEW)
- PWA manifest with icons, shortcuts, display mode

### static/sw.js (NEW)
- Cache-first for static assets
- Network-first for API calls and HTML pages
- Offline fallback to cached homepage

### static/favicon.svg (NEW)
- SVG store/market icon with amber brand color

### .env.example (NEW)
- Documents all required and optional environment variables
- Security warnings for production deployment

---

## Previous (v1.0) — baseline
- Basic Flask MPA with SQLite, single-column mobile layout
- OTP login, market/lot/booking flow, simple chat
- Admin users page, basic owner console
