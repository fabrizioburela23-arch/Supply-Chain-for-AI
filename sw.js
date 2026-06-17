/* Khipu Finance v1 — Service Worker
   App-shell cache-first + API network-first con fallback a caché (uso offline).
   Servido por server.py en /sw.js con cabecera Service-Worker-Allowed: / */
const CACHE = 'khipu-finance-v1';
const SHELL = ['/', '/app.html',
  '/nodes/nodes_spacex.js', '/nodes/nodes_expand.js', '/nodes/nodes_expand2.js',
  '/engine/graph3d.js', '/engine/hypergraph.js', '/engine/voice.js',
  '/engine/secondbrain.js', '/sim/mirofish_client.js', '/sim/scenario_builder.js',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = req.url;
  const isData = url.includes('/api/') || url.includes('finnhub.io') ||
                 url.includes('financialmodelingprep.com') || url.includes('marketstack.com');

  if (isData) {
    // network-first: intenta la red, cae a caché si falla (offline)
    e.respondWith(
      fetch(req).then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(req, clone)).catch(() => {});
        return res;
      }).catch(() => caches.match(req))
    );
  } else {
    // app shell + CDN: cache-first, rellena en segundo plano
    e.respondWith(
      caches.match(req).then(cached => cached || fetch(req).then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(req, clone)).catch(() => {});
        return res;
      }))
    );
  }
});
