# Smart Hawker — Design System v2.0

## Overview

Smart Hawker uses a pure CSS custom-property design token system with zero build-step dependencies. All design decisions flow from a single source: `static/css/styles.css` (tokens) + `static/js/theme.js` (runtime theme switching).

---

## Color System

### HSL Brand Scale

Accent color is fully dynamic via two CSS variables on `<html>`:

```css
--brand-h: 36;     /* hue (0–360) */
--brand-s: 82%;    /* saturation */
```

The full brand scale is derived from these two variables:

| Token            | Usage                          |
|------------------|--------------------------------|
| `--brand-50`     | Lightest tint, backgrounds     |
| `--brand-100`    | Hover states, soft backgrounds |
| `--brand-200`    | Focus rings, active borders    |
| `--brand-500`    | Primary buttons, links         |
| `--brand-700`    | Dark text on light background  |
| `--brand-900`    | Darkest shade                  |
| `--brand`        | = `--brand-500` (shorthand)    |
| `--brand-ink`    | High-contrast text on brand    |
| `--brand-soft`   | = `--brand-100` (shorthand)    |

### Semantic Tokens

| Token               | Light                 | Dark                   |
|---------------------|-----------------------|------------------------|
| `--bg`              | `#fafafa`             | `#0e0f14`              |
| `--bg-2`            | `#f1f3f9`             | `#16181f`              |
| `--surface`         | `#ffffff`             | `#1c1e26`              |
| `--ink`             | `#111318`             | `#eef0f8`              |
| `--ink-2`           | `#374151`             | `#c2c6d4`              |
| `--ink-soft`        | `#6b7280`             | `#8b92a8`              |
| `--ink-ghost`       | `#9ca3af`             | `#5a6075`              |
| `--line`            | `#e5e7eb`             | `#2a2d3a`              |
| `--danger`          | `hsl(4,72%,52%)`      | `hsl(4,72%,58%)`       |
| `--danger-soft`     | `hsl(4,72%,96%)`      | `hsl(4,45%,14%)`       |
| `--danger-ink`      | `hsl(4,72%,38%)`      | `hsl(4,72%,72%)`       |
| `--success`         | `hsl(156,60%,40%)`    | `hsl(156,60%,46%)`     |
| `--success-soft`    | `hsl(156,60%,94%)`    | `hsl(156,30%,12%)`     |
| `--success-ink`     | `hsl(156,60%,28%)`    | `hsl(156,60%,68%)`     |
| `--warn`            | `hsl(36,92%,50%)`     | `hsl(36,92%,55%)`      |
| `--warn-soft`       | `hsl(36,92%,94%)`     | `hsl(36,50%,12%)`      |
| `--warn-ink`        | `hsl(36,92%,32%)`     | `hsl(36,92%,70%)`      |

### Accent Themes

Six preset accent hues:

| Key       | Hue | Saturation | Thai Label            |
|-----------|-----|------------|-----------------------|
| `amber`   | 36  | 82%        | อำพัน (ค่าเริ่มต้น) |
| `teal`    | 168 | 76%        | เขียวมรกต            |
| `indigo`  | 235 | 78%        | คราม                  |
| `rose`    | 345 | 78%        | ชมพูอมแดง           |
| `violet`  | 262 | 70%        | ม่วง                  |
| `emerald` | 142 | 72%        | มรกต                  |

---

## Typography

```css
--font-sans: "IBM Plex Sans Thai", "Sarabun", system-ui, sans-serif;

/* Scale */
--text-xs:   0.72rem   /* 11.5px */
--text-sm:   0.85rem   /* 13.6px */
--text-base: 1rem      /* 16px */
--text-lg:   1.1rem    /* 17.6px */
--text-xl:   1.25rem   /* 20px */
--text-2xl:  1.5rem    /* 24px */
--text-3xl:  2rem      /* 32px */
```

**Senior mode** (`data-senior="1"` on `<html>`): scales base to 18px, increases line-height to 1.75, larger touch targets.

---

## Spacing

8px grid via CSS variables:

```css
--s1: 4px   --s2: 8px   --s3: 12px  --s4: 16px
--s5: 20px  --s6: 24px  --s7: 28px  --s8: 32px
--s10: 40px --s12: 48px --s16: 64px
```

---

## Layout

### Responsive Shell — 3-Tier (V5)

Smart Hawker uses a 3-tier responsive layout. The breakpoints are designed to cover phone, tablet (iPad), and desktop classes.

| Breakpoint       | Device class          | Sidebar                          | Bottom nav |
|------------------|-----------------------|----------------------------------|------------|
| < 768px          | Phone                 | Hidden                           | Visible (5 items + more-sheet) |
| 768px – 1023px   | Tablet / iPad         | Icon-rail (72px, icons-only)     | Hidden |
| ≥ 1024px         | Desktop / iPad Pro    | Full width (248px, icons + text) | Hidden |

```
.app-shell
  ├── .sidebar                      (72px @ tablet, 248px @ desktop, hidden @ phone)
  │     ├── .sidebar-brand          (icon-only @ tablet, icon+text @ desktop)
  │     ├── .sidebar-section        (hidden @ tablet via display:none !important)
  │     ├── .sidebar-link           (centered, no text @ tablet)
  │     └── .sidebar-footer
  └── .content-wrap                 (margin-left: 72px @ tablet, 248px @ desktop, 0 @ phone)
        ├── [page content]
        └── .bottomnav              (visible @ phone only; .app-shell.shell-bare has no margin)
```

#### Icon-rail pattern (tablet 768–1023px)

- `.sidebar-brand-name`, `.sidebar-link > span`, `.sidebar-section` → `display:none !important`
- `.sidebar-link` → `justify-content:center; padding: var(--s3) 0`
- All links must have `title="..."` for hover tooltip accessibility
- `.content-wrap` → `margin-left: 72px` (matches icon-rail width)
- `.bottomnav` → `display:none !important` (not needed at tablet+)

#### More-sheet (phone)

When more than 5 nav items exist, a slide-up bottom sheet (`#more-sheet`) contains overflow links. Opened via `openMoreSheet()` / `closeMoreSheet()`. Backdrop closes it. All civic-tech pages accessible here.

#### Utility classes

| Class           | Effect                                              |
|-----------------|-----------------------------------------------------|
| `.hide-tablet`  | `display:none` at 768–1023px                        |
| `.table-scroll` | `overflow-x:auto` wrapper for wide tables on mobile |

### Key Layout Variables

```css
--sidebar-w:  248px
--topbar-h:   56px
--bottomnav-h: 60px
--page-max:   680px
--content-pad: var(--s5)
```

### Page Containers

| Class         | Description                             |
|---------------|-----------------------------------------|
| `.page`       | `max-width: var(--page-max)`, centered  |
| `.page-pad`   | `padding: var(--content-pad)`           |
| `.page-inner` | Narrower content column (480px max)     |
| `.px`         | Horizontal padding only                 |
| `.container`  | Full-width, no max                      |

---

## Components

### Buttons

| Variant         | Usage                            |
|-----------------|----------------------------------|
| `.btn-primary`  | Main CTA                         |
| `.btn-soft`     | Secondary, less contrast         |
| `.btn-ghost`    | Tertiary, border only            |
| `.btn-danger`   | Destructive actions              |
| `.btn-icon`     | Square icon-only button          |
| `.btn-block`    | Full-width                       |
| `.btn-sm`       | Small size                       |

All buttons: `min-height: 44px` (WCAG touch target), `focus-visible` outline.

### Cards

```css
.card           /* base card with surface bg + border + shadow */
.card-press     /* adds hover/active press effect */
.card.pad       /* adds internal padding */
```

### Chips

```css
.chip           /* neutral pill label */
.chip-accent    /* brand accent color */
.chip-danger    /* danger red */
.chip-sm        /* smaller size */
.chip-active    /* selected state (used in filter groups) */
```

### Avatar

```css
.avatar         /* circular, flexbox centered, deterministic bg via avaColor() */
```

### Toast Notifications

Injected into `#toast-root`. Never use `alert()` or `confirm()` except for destructive double-confirm flows.

```javascript
Toast.success("ข้อความ")
Toast.error("ข้อความ")
Toast.warn("ข้อความ")
Toast.info("ข้อความ")
```

### OTP Input

Six `.otp-cell` inputs inside `.otp-cells`:
- Auto-advance on input
- Paste from clipboard fills all 6 cells
- Backspace goes to previous cell
- Enter triggers verify

### Stat Cards

```css
.stat-card      /* KPI card with icon, large number, label */
```

### Lot Row

```css
.lot-row        /* flex row for lot list in owner console */
```

---

## Icons

[Lucide Icons](https://lucide.dev) via CDN UMD build. Usage:

```html
<i data-lucide="store" style="width:20px;height:20px" aria-hidden="true"></i>
```

Call `icons()` or `icons(containerEl)` after inserting dynamic HTML to activate Lucide icons.

---

## FOUC Prevention

`static/js/theme.js` is loaded **synchronously** in `<head>` **before** CSS link tags. It reads `localStorage` and sets `data-theme`, `--brand-h`, `--brand-s`, `data-accent`, `data-senior`, and `lang` on `<html>` before the first CSS parse. This means zero flash-of-unstyled/wrong-theme content.

---

## Accessibility (WCAG 2.2 AA)

- All interactive elements: `min-height: 44px`, `min-width: 44px` (touch target)
- `focus-visible`: `3px solid var(--brand)` outline, `outline-offset: 2px`
- `prefers-reduced-motion`: all animations reduced to `0.01ms` duration
- All icons decorative: `aria-hidden="true"`; meaningful icons get `aria-label` on parent
- OTP group: `aria-label` on container, individual `aria-label` on each cell
- Role pickers: `role="radiogroup"` + `aria-checked` on each option
- Toasts: `role="status"` or `role="alert"` with `aria-live`
- Forms: explicit `<label for="...">` on all inputs
- Error messages: `role="alert"` + `aria-live="polite"`
- Chat log: `role="log"` + `aria-live="polite"`

---

## Anti-Mismatch Architecture

Single source of truth for all enum strings:

```
constants.py
    ↓ CLIENT_CONFIG dict
app.py context_processor → window.CONFIG (Jinja2 → <script>)
    ↓
app.js → const C = window.CONFIG
    ↓
All JS uses C.BOOKING_STATUS.CONFIRMED, C.ROLE_LABEL.SELLER, etc.
```

**Never** hardcode a string like `"CONFIRMED"` in a template or JS file — always reference `C.BOOKING_STATUS.CONFIRMED`.

---

## API Client Contract

All API endpoints return exactly:

```json
{ "ok": true, ...payload }
{ "ok": false, "error": "human-readable message" }
```

Never return HTTP error codes for business logic errors — always `200 + ok:false`.
HTTP 4xx/5xx only for unrecoverable errors (auth, server crash).

The JS API client (`API.get/post/patch/put/del`) always resolves (never rejects) and returns the JSON object or `{ ok: false, error: "..." }` on network failure.

---

## PWA

- `static/manifest.webmanifest` — name, icons, start_url, display: standalone, shortcuts
- `static/sw.js` — cache-first static, network-first API, offline HTML fallback
- Service worker registered in `app.js` `DOMContentLoaded`

---

## i18n

String table in `constants.py → STRINGS → CLIENT_CONFIG → window.CONFIG.STRINGS`.

```javascript
function t(key) {
  const lang = THEME.currentLang ? THEME.currentLang() : "th";
  const strings = (window.CONFIG && window.CONFIG.STRINGS) || {};
  return (strings[key] && strings[key][lang]) || key;
}
```

Usage: `t("book_now")` → `"จองเลย"` (TH) or `"Book Now"` (EN).

---

## Map Integration

- [Leaflet.js](https://leafletjs.com/) 1.9.4 + OpenStreetMap tiles
- [Leaflet.markercluster](https://github.com/Leaflet/Leaflet.markercluster) 1.5.3
- [Nominatim](https://nominatim.openstreetmap.org) for geocoding (search) and reverse geocoding (auto-fill province/district)
- Google Maps deep link for navigation: `https://www.google.com/maps/dir/?api=1&destination=<lat>,<lng>`

---

## PromptPay QR

Generated server-side via `promptpay.py` (EMVCo payload builder). QR is served as PNG via `/api/payments/<booking_id>/qr.png`. The `depositAmount` is 50% of total rent; idempotent — already-paid bookings return `ok:true` immediately.
