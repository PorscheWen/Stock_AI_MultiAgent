// 持股操作建議 PWA - Service Worker
const CACHE = 'stock-pwa-v1';
const PRECACHE = ['/app', '/static/manifest.json'];

// Install: precache shell
self.addEventListener('install', e => {
    e.waitUntil(
        caches.open(CACHE)
            .then(c => c.addAll(PRECACHE))
            .then(() => self.skipWaiting())
    );
});

// Activate: clear old caches
self.addEventListener('activate', e => {
    e.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

// Fetch strategy:
// - API calls  → network only (always fresh data)
// - App shell  → cache first, then network
self.addEventListener('fetch', e => {
    const url = e.request.url;

    // API: network only
    if (url.includes('/api/')) {
        e.respondWith(fetch(e.request));
        return;
    }

    // App shell: cache first
    e.respondWith(
        caches.match(e.request).then(cached => {
            const network = fetch(e.request).then(resp => {
                if (resp && resp.status === 200 && e.request.method === 'GET') {
                    const clone = resp.clone();
                    caches.open(CACHE).then(c => c.put(e.request, clone));
                }
                return resp;
            }).catch(() => null);
            return cached || network;
        })
    );
});
