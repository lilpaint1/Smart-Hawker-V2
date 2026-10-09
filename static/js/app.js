/* ===== Smart Hawker — app.js (shared helpers, loaded on every page) ===== */

/* ---- API client — ALL fetches go through here ---- */
const API = {
  async req(path, method = "GET", body, opts = {}) {
    const timeout  = opts.timeout  || 12000;
    const retries  = opts.retries  !== undefined ? opts.retries : (method === "GET" ? 1 : 0);
    const ctrl     = new AbortController();
    const timer    = setTimeout(() => ctrl.abort(), timeout);
    try {
      const options = { method, headers: {}, signal: ctrl.signal };
      if (body !== undefined && body !== null) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
      }
      const res = await fetch("/api" + path, options);
      clearTimeout(timer);
      try   { return await res.json(); }
      catch { return { ok: false, error: "เซิร์ฟเวอร์ตอบผิดรูปแบบ" }; }
    } catch (e) {
      clearTimeout(timer);
      if (e.name === "AbortError") return { ok: false, error: "หมดเวลา กรุณาลองใหม่" };
      if (retries > 0) return this.req(path, method, body, { ...opts, retries: retries - 1 });
      return { ok: false, error: "ไม่สามารถเชื่อมต่อได้" };
    }
  },
  get(p, o)    { return this.req(p, "GET", undefined, o); },
  post(p, b, o){ return this.req(p, "POST", b, o); },
  patch(p, b)  { return this.req(p, "PATCH", b); },
  put(p, b)    { return this.req(p, "PUT", b); },
  del(p)       { return this.req(p, "DELETE"); },
};

/* ---- Constants from server (anti-mismatch) ---- */
const C  = window.CONFIG || {};
const ME = window.ME    || null;

/* ---- i18n helper ---- */
var _LANG = (window.THEME && window.THEME.currentLang) ? window.THEME.currentLang() : 'th';
function t(key) {
  var s = (C.STRINGS || {})[key];
  if (!s) return key;
  return s[_LANG] || s['th'] || key;
}

/* ---- DOM helpers ---- */
function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls)      e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
}
function $(sel, ctx)  { return (ctx || document).querySelector(sel); }
function $$(sel, ctx) { return [...(ctx || document).querySelectorAll(sel)]; }
function esc(s) {
  const d = document.createElement("div");
  d.textContent = (s == null ? "" : String(s));
  return d.innerHTML;
}
function escAttr(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
function thb(n)      { return "฿" + Number(n).toLocaleString("th-TH"); }
function fmtDate(iso){ return new Date(iso).toLocaleDateString("th-TH", { year:"numeric", month:"short", day:"numeric" }); }
function fmtTime(iso){ return new Date(iso).toLocaleTimeString("th-TH", { hour:"2-digit", minute:"2-digit" }); }
function qs(name)    { return new URLSearchParams(location.search).get(name); }
function go(url)     { location.href = url; }

/* ---- Avatar colours ---- */
const AVA = ["#e06090","#0d9488","#7c3aed","#db2777","#2563eb","#16a34a","#dc2626","#0284c7"];
function avaColor(seed) {
  let h = 0;
  for (let i = 0; i < (seed || "").length; i++) h = (h * 31 + seed.charCodeAt(i)) | 0;
  return AVA[Math.abs(h) % AVA.length];
}
function avatarEl(name, size = 44, radius = "50%") {
  const c = avaColor(name);
  const d = el("div", "avatar", esc((name || "?").charAt(0).toUpperCase()));
  d.style.cssText = `width:${size}px;height:${size}px;background:${c};border-radius:${radius};font-size:${size*.45}px`;
  return d;
}

/* ---- Star rating HTML ---- */
function stars(n, size = 14) {
  let h = "";
  const rounded = Math.round(n || 0);
  for (let i = 1; i <= 5; i++) {
    const filled = i <= rounded ? "var(--warn)" : "none";
    h += `<i data-lucide="star" style="width:${size}px;height:${size}px;color:var(--warn);fill:${filled}"></i>`;
  }
  return `<span class="stars" style="display:inline-flex;gap:1px">${h}</span>`;
}

/* ---- Lucide icons ---- */
function icons(root) {
  if (window.lucide) window.lucide.createIcons(root ? { rootElement: root } : undefined);
}

/* ---- Toast notifications ---- */
const Toast = {
  show(msg, type = "info", dur = 3500) {
    const root = document.getElementById("toast-root");
    if (!root) return;
    const t = el("div", `toast toast-${type}`, esc(msg));
    root.appendChild(t);
    requestAnimationFrame(() => requestAnimationFrame(() => t.classList.add("show")));
    setTimeout(() => {
      t.classList.remove("show");
      setTimeout(() => t.remove(), 320);
    }, dur);
  },
  success(m, d) { this.show(m, "success", d); },
  error(m, d)   { this.show(m, "error",   d); },
  warn(m, d)    { this.show(m, "warn",    d); },
  info(m, d)    { this.show(m, "info",    d); },
};

/* ---- Confirm dialog — themed modal, no native confirm() ---- */
function confirmDialog(msg, opts = {}) {
  return new Promise(resolve => {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", opts.title || "ยืนยัน");
    overlay.innerHTML = `<div class="modal-box">
      <div class="modal-title">${opts.title ? esc(opts.title) : "ยืนยันการดำเนินการ?"}</div>
      <div class="modal-body">${esc(msg)}</div>
      <div class="modal-footer">
        <button class="btn btn-ghost flex1" id="mdl-cancel" type="button">ยกเลิก</button>
        <button class="btn btn-danger flex1" id="mdl-ok" type="button">${opts.okLabel || "ยืนยัน"}</button>
      </div>
    </div>`;
    document.body.appendChild(overlay);
    requestAnimationFrame(() => requestAnimationFrame(() => overlay.classList.add("show")));
    const close = v => {
      overlay.classList.remove("show");
      setTimeout(() => overlay.remove(), 240);
      resolve(v);
    };
    overlay.querySelector("#mdl-ok").addEventListener("click", () => close(true));
    overlay.querySelector("#mdl-cancel").addEventListener("click", () => close(false));
    overlay.addEventListener("click", e => { if (e.target === overlay) close(false); });
    const onKey = e => { if (e.key === "Escape") { document.removeEventListener("keydown", onKey); close(false); } };
    document.addEventListener("keydown", onKey);
    setTimeout(() => { const btn = overlay.querySelector("#mdl-cancel"); if (btn) btn.focus(); }, 60);
  });
}

/* ---- Loading state on buttons ---- */
function setBtnLoading(btn, loading) {
  if (!btn) return;
  if (loading) {
    btn._origText  = btn.innerHTML;
    btn._origWidth = btn.offsetWidth;
    btn.style.minWidth = btn._origWidth + "px";
    btn.innerHTML = '<i data-lucide="loader-2" style="width:18px;height:18px;animation:spin 1s linear infinite"></i>';
    btn.disabled  = true;
    icons(btn);
    // add spin keyframe once
    if (!document.getElementById("spin-kf")) {
      const s = document.createElement("style");
      s.id = "spin-kf";
      s.textContent = "@keyframes spin{to{transform:rotate(360deg)}}";
      document.head.appendChild(s);
    }
  } else {
    btn.innerHTML = btn._origText || "";
    btn.disabled  = false;
    btn.style.minWidth = "";
    icons(btn);
  }
}

/* ---- Debounce ---- */
function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

/* ---- Bell notification badge ---- */
async function refreshBell() {
  if (document.hidden) return;
  const b = $("#bell-badge");
  if (!b || !ME || !ME.id) return;
  const d = await API.get("/notifications");
  if (!d.ok) return;
  const n = d.unread || 0;
  if (n > 0) { b.textContent = n > 9 ? "9+" : n; b.classList.remove("hide"); }
  else b.classList.add("hide");
}

/* ---- Sidebar active link — most-specific match only (parent never co-highlights child) ---- */
function setActiveSidebarLink() {
  const path  = location.pathname;
  const links = $$(".sidebar-link[href]");
  links.forEach(a => a.classList.remove("active"));
  let best = null, bestLen = -1;
  links.forEach(a => {
    const href    = a.getAttribute("href");
    const matched = path === href || (href !== "/" && path.startsWith(href + "/"));
    if (matched && href.length > bestLen) { best = a; bestLen = href.length; }
  });
  if (best) best.classList.add("active");
}

/* ---- Favorite toggle (market cards) ---- */
async function toggleFav(marketId, btn) {
  if (!ME || !ME.id) { go("/login?next=" + location.pathname); return; }
  const isFav = btn.dataset.fav === "1";
  const method = isFav ? "del" : "post";
  const d = await API[method](`/favorites/${marketId}`);
  if (!d.ok) { Toast.error(d.error); return; }
  btn.dataset.fav = d.isFav ? "1" : "0";
  const ic = btn.querySelector("i");
  if (ic) ic.style.fill = d.isFav ? "currentColor" : "none";
  Toast.success(d.isFav ? "เพิ่มในรายการโปรดแล้ว" : "นำออกจากรายการโปรด");
}

/* ---- Skeleton helpers ---- */
function skelCards(n = 3, cls = "") {
  return Array.from({length: n}, () =>
    `<div class="card pad row gap3 mt2 ${cls}">
      <div class="skeleton" style="width:52px;height:52px;border-radius:14px;flex-shrink:0"></div>
      <div class="flex1 col gap2">
        <div class="skeleton" style="height:16px;width:60%"></div>
        <div class="skeleton" style="height:12px;width:40%"></div>
      </div>
    </div>`
  ).join("");
}

/* ---- URL safety validator — only allow https?:// ---- */
function safeUrl(url) {
  if (!url) return "";
  return /^https?:\/\//i.test(url) ? url : "";
}

/* ---- Market card HTML builder ---- */
function marketCardHTML(m, compact = false) {
  const initial = (m.name || "ต").replace(/ตลาด|Market/gi, "").trim().charAt(0) || "ต";
  const price   = m.minPrice ? `เริ่ม ${thb(m.minPrice)}/วัน` : "เต็ม";
  const avail   = m.availableLots || 0;
  const tags    = (m.tags || []).slice(0, 2).map(tg => `<span class="chip" style="font-size:.65rem;padding:1px 7px">${esc(tg)}</span>`).join("");
  const badgeV  = m.isVerified ? `<i data-lucide="badge-check" style="width:13px;color:var(--accent)" title="พื้นที่ผ่านการรับรอง"></i>` : "";
  // Verified owner badge
  const ownerBadge = m.ownerVerified ? `<i data-lucide="shield-check" style="width:12px;color:var(--success)" title="เจ้าของยืนยันตัวตนแล้ว"></i>` : "";
  // GOV / PRIVATE badge
  const govBadge = m.ownerType === "GOV"
    ? `<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:20px;font-size:.65rem;font-weight:700;background:hsl(205,78%,92%);color:hsl(205,70%,30%)" title="เปิดโดยภาครัฐ"><i data-lucide="landmark" style="width:10px;height:10px"></i>ภาครัฐ</span>`
    : "";
  const favFill = m.isFav ? "currentColor" : "none";
  const ratingHTML = m.avgRating ? `${stars(m.avgRating, 12)}<span class="muted" style="font-size:.7rem">${m.avgRating} (${m.reviewCount})</span>` : `<span class="ghost" style="font-size:.72rem">ยังไม่มีรีวิว</span>`;
  // Only allow https?:// URLs for cover images; local /static/ paths are also safe
  const coverUrl = m.coverPhotoUrl
    ? (/^https?:\/\//i.test(m.coverPhotoUrl) || /^\/static\//i.test(m.coverPhotoUrl)
        ? m.coverPhotoUrl : "")
    : "";

  if (compact) {
    return `<div class="card card-press pad row gap3" style="cursor:pointer" onclick="go('/market/${escAttr(m.id)}')">
      <div class="avatar" style="width:50px;height:50px;border-radius:14px;background:${avaColor(m.name)};font-size:20px;font-weight:800">${esc(initial)}</div>
      <div class="flex1">
        <div class="row gap1"><span class="title truncate">${esc(m.name)}</span>${badgeV}${ownerBadge}</div>
        <div class="muted sub row gap1 mt1"><i data-lucide="map-pin" style="width:12px;height:12px"></i>${esc(m.district||"")}${m.district?", ":""}${esc(m.province)}</div>
        <div class="row gap2 mt1">${ratingHTML}</div>
      </div>
      <div class="col" style="align-items:flex-end;gap:4px">
        <span class="price" style="font-size:.82rem">${price}</span>
        <span class="muted" style="font-size:.7rem">ว่าง <b style="color:${avail?"var(--accent-ink)":"var(--danger)"}">${avail}</b>/${m.totalLots||0}</span>
      </div>
    </div>`;
  }

  return `<div class="market-card" onclick="go('/market/${escAttr(m.id)}')" tabindex="0" role="button" aria-label="${escAttr(m.name)}">
    <div class="cover">
      <div class="cover-gradient"></div>
      <div class="cover-init">${esc(initial)}</div>
      ${coverUrl ? `<img src="${escAttr(coverUrl)}" alt="${escAttr(m.name)}" loading="lazy" onerror="this.remove()">
                   <div class="cover-overlay"></div>` : ""}
      <button class="btn btn-icon sm" style="position:absolute;top:8px;right:8px;background:rgba(0,0,0,.35);color:#fff;backdrop-filter:blur(4px);border:none;z-index:10;min-height:0"
        data-fav="${escAttr(m.isFav ? 1 : 0)}" onclick="event.stopPropagation();toggleFav('${escAttr(m.id)}',this)" aria-label="บันทึกในรายการโปรด">
        <i data-lucide="heart" style="width:16px;height:16px;fill:${favFill}"></i>
      </button>
      ${m.isFeatured ? `<span class="chip" style="position:absolute;bottom:8px;left:8px;background:var(--warn);color:#fff;font-size:.65rem;z-index:10">แนะนำ</span>` : ""}
    </div>
    <div class="body">
      <div class="row gap1 mb1"><span class="title truncate flex1">${esc(m.name)}</span>${badgeV}${govBadge}</div>
      <div class="muted small row gap1" style="margin-bottom:.4rem">
        <i data-lucide="map-pin" style="width:12px;height:12px"></i>${esc(m.district||"")}${m.district?", ":""}${esc(m.province)}
      </div>
      <div class="row gap1" style="margin-bottom:.4rem">${ratingHTML}</div>
      <div class="row gap1 wrap">${tags}</div>
      <div class="between mt2" style="padding-top:.5rem;border-top:1px solid var(--line)">
        <span class="muted small">ว่าง <b style="color:${avail?"var(--accent-ink)":"var(--danger)"}">${avail}</b>/${m.totalLots||0} ล็อก${ownerBadge}</span>
        <span class="price small">${price}</span>
      </div>
    </div>
  </div>`;
}

/* ---- Global logout ---- */
async function logout() {
  try { await API.post("/auth/logout"); } finally { go("/"); }
}

/* ---- Global JS error surface (catch unhandled crashes) ---- */
window.addEventListener("error", e => {
  if (typeof Toast !== "undefined") Toast.error("เกิดข้อผิดพลาด: " + (e.message || e.type));
});
window.addEventListener("unhandledrejection", e => {
  if (typeof Toast !== "undefined") Toast.error("คำขอล้มเหลว กรุณาลองใหม่");
});

/* ---- DOMContentLoaded setup ---- */
document.addEventListener("DOMContentLoaded", () => {
  icons();
  refreshBell();
  setInterval(refreshBell, 10000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refreshBell(); });
  setActiveSidebarLink();

  // PWA service worker
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {});
  }

  // Theme toggle button in sidebar (if present)
  const themeToggle = document.getElementById("theme-toggle");
  if (themeToggle && window.THEME) {
    const updateIcon = () => {
      const ic = themeToggle.querySelector("i");
      const sp = themeToggle.querySelector("span");
      if (ic) ic.setAttribute("data-lucide", THEME.current() === "dark" ? "sun" : "moon");
      if (sp) sp.textContent = THEME.current() === "dark" ? "โหมดสว่าง" : "โหมดมืด";
      icons(themeToggle);
    };
    themeToggle.addEventListener("click", () => { THEME.toggle(); updateIcon(); });
    updateIcon();
  }
});
