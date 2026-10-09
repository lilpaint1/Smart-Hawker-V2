// Smart Hawker Service Worker v1.0
const CACHE_NAME = "smart-hawker-v4";
const STATIC_ASSETS = [
  "/static/css/styles.css",
  "/static/js/app.js",
  "/static/js/theme.js",
  "/static/manifest.webmanifest",
  "/static/favicon.svg",
];

// ---- Install: pre-cache static assets ----
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return Promise.allSettled(STATIC_ASSETS.map(url => cache.add(url).catch(() => {})));
    }).then(() => self.skipWaiting())
  );
});

// ---- Activate: remove old caches ----
self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// ---- Fetch: cache-first for static, network-first for API/pages ----
self.addEventListener("fetch", event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip cross-origin, POST, and non-GET
  if (request.method !== "GET" || url.origin !== location.origin) return;

  // API: network-first, fall back to cache
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(request)
        .then(res => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          }
          return res;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Static assets: cache-first
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached;
        return fetch(request).then(res => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          }
          return res;
        });
      })
    );
    return;
  }

  // HTML pages: network-first, offline fallback
  if (request.headers.get("accept") && request.headers.get("accept").includes("text/html")) {
    event.respondWith(
      fetch(request)
        .then(res => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          }
          return res;
        })
        .catch(() =>
          caches.match(request).then(cached => cached || caches.match("/"))
        )
    );
    return;
  }
});
