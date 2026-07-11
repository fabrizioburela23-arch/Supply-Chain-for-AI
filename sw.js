/* Khipu Finance — Service Worker
   Código propio (HTML/JS/CSS same-origin) y API: NETWORK-FIRST → siempre la
   última versión cuando hay red, con caché solo como respaldo offline.
   CDNs externos inmutables (cdnjs/jsdelivr/unpkg/fonts): cache-first.
   Servido por server.py en /sw.js con cabecera Service-Worker-Allowed: / */
const CACHE = 'khipu-finance-v61';
// SHELL = exactamente los <script src> de app.html + la propia app.
// Si añades/quitas un <script src>, refleja el cambio aquí Y bumpea CACHE.
const SHELL = ['/', '/app.html',
  '/vendor/d3.min.js', '/vendor/three.min.js', '/vendor/chart.umd.min.js',
  '/vendor/satellite.min.js',
  '/nodes/nodes_seed.js',
  '/nodes/nodes_expand.js', '/nodes/nodes_expand2.js', '/nodes/nodes_spacex.js',
  '/nodes/nodes_expand3.js', '/nodes/nodes_nuclear.js', '/nodes/nodes_expand4.js',
  '/nodes/nodes_expand5.js',
  '/nodes/preipo_intel.js',
  '/nodes/links_all.js', '/nodes/merge_graph.js', '/nodes/links_expand.js', '/nodes/links_connect.js',
  '/engine/graph3d.js', '/engine/hypergraph.js', '/engine/voice.js',
  '/engine/secondbrain.js', '/engine/geo_coords.js', '/engine/planetarium.js',
  '/engine/geoglobe.js', '/engine/canvas-data.js', '/engine/command_center.js',
  '/engine/temporal-graph.js', '/nodes/temporal_seed_facts.js',
  '/nodes/temporal_seed_facts2.js', '/nodes/ontology.js', '/nodes/ontology_facts.js',
  '/engine/khipu_lang.js', '/engine/guide.js', '/engine/xray.js', '/engine/insights.js', '/engine/statematrix.js', '/engine/livesim.js', '/engine/layers.js', '/engine/brief.js', '/engine/compare.js', '/engine/matrixview.js', '/engine/nav4.js', '/engine/cockpit.js', '/engine/live.js', '/engine/localcharts.js', '/engine/fincard.js',
  '/sim/mirofish_client.js', '/sim/scenario_builder.js',
];

self.addEventListener('install', e => {
  // Precarga del shell pero no falla la instalación si algo no está
  e.waitUntil(
    caches.open(CACHE).then(c => Promise.allSettled(SHELL.map(u => c.add(u))))
      .then(() => self.skipWaiting())
  );
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
  let sameOrigin = false;
  try { sameOrigin = new URL(req.url).origin === self.location.origin; } catch (_) {}

  if (sameOrigin) {
    // Código propio + API → network-first (siempre lo último online; caché = offline)
    // ignoreSearch: el server versiona los <script src> con ?v=N — el fallback
    // offline debe encontrar el archivo aunque la query cambie.
    e.respondWith(
      fetch(req).then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(req, clone)).catch(() => {});
        return res;
      }).catch(() => caches.match(req, { ignoreSearch: true }).then(m => m || Response.error()))
    );
  } else {
    // CDNs externos inmutables → cache-first
    e.respondWith(
      caches.match(req).then(cached => cached || fetch(req).then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(req, clone)).catch(() => {});
        return res;
      }))
    );
  }
});
