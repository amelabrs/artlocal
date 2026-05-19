// ArtLocal Service Worker (basic caching)
const CACHE_NAME = "artlocal-v1";

self.addEventListener("install", (e) => {
    self.skipWaiting();
});

self.addEventListener("activate", (e) => {
    e.waitUntil(clients.claim());
});

self.addEventListener("fetch", (e) => {
    // Network-first for API calls, cache-first for static assets
    if (e.request.url.includes("/api/")) {
        e.respondWith(fetch(e.request));
    } else {
        e.respondWith(
            caches.match(e.request).then(cached => cached || fetch(e.request))
        );
    }
});
