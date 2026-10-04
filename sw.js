/* Khipu Finance — Service Worker
   Servido por server.py en /sw.js con cabecera Service-Worker-Allowed: /
   CACHE va en la línea 6 (regla de despliegue #1: bump vN → vN+1 en cada
   cambio de JS/HTML). server.py (_sw_version) lee SOLO los primeros 2048
   caracteres para inyectar ?v=N en los <script src> — no la bajes. */
const CACHE = 'khipu-finance-v198';
/* Reglas (auditoría estructural 2026-09-30, hallazgo #3 — incidente real: un
   502 HTML de Railway quedó guardado y se servía offline → "Unexpected token
   '<'", y /api/health cacheado devolvía {server:true} ocultando el aviso):
   - API (/api, /v1, /mcp, /oauth, /.well-known): NUNCA se cachea. Red directa;
     si la red falla o llega un ≥500 que no es JSON (página de error del
     proxy) → JSON 503 {error, error_en, offline:true} con no-store.
   - Navegaciones (la app): red con ~10 s de espera; si falla, tarda de más o
     responde ≥500 → último shell guardado con window.__KHIPU_STALE_SHELL=1
     inyectado tras <head> (app.html muestra al instante la franja roja
     "servidor no disponible").
   - Código propio (JS/CSS/vendor same-origin): se guarda SOLO si res.ok &&
     res.type==='basic' (nunca errores). URL versionada (?v=N) ya guardada →
     caché (inmutable); si no, red primero (≤8 s si hay copia) y, sin red,
     ≥500 o tiempo agotado, copia guardada (ignoreSearch: el server versiona
     los <script src> con ?v=N). La instalación precarga YA las URLs ?v=N
     exactas (N = número de CACHE, el mismo que inyecta server.py) para que
     el primer shell viejo tras un despliegue arranque sin esperar a la red.
   - Modo degradado: si una navegación tuvo que servir el shell viejo (server
     caído o colgado), durante 60 s el código propio con copia guardada se
     sirve directo del caché (sin esperar a un server que no contesta).
   - El shell viejo conserva las cabeceras de seguridad de la copia guardada
     (CSP, frame-ancestors, X-Frame-Options, nosniff…).
   - CDNs externos inmutables (cdnjs/jsdelivr/unpkg/fonts): cache-first, y
     solo respuestas buenas (res.ok). Excepción: la hoja de estilos de Google
     Fonts (opaca, no se puede leer su status) — un error ahí solo cambia la
     tipografía, nunca rompe la app. Cualquier otro origen: sin intervenir. */
// SHELL = exactamente los <script src> de app.html + la propia app.
// Si añades/quitas un <script src>, refleja el cambio aquí Y bumpea CACHE.
const SHELL = ['/', '/app.html',
  '/vendor/d3.min.js', '/vendor/three.min.js', '/vendor/chart.umd.min.js',
  '/vendor/satellite.min.js',
  '/nodes/nodes_seed.js',
  '/nodes/nodes_expand.js', '/nodes/nodes_expand2.js', '/nodes/nodes_spacex.js',
  '/nodes/nodes_expand3.js', '/nodes/nodes_nuclear.js', '/nodes/nodes_expand4.js',
  '/nodes/nodes_expand5.js', '/nodes/meta_fill.js', '/nodes/nodes_china.js', '/nodes/nodes_multicapa.js',
  '/nodes/preipo_intel.js', '/nodes/listing_status.js', '/nodes/private_valuations.js',
  '/nodes/links_all.js', '/nodes/merge_graph.js', '/nodes/links_expand.js', '/nodes/links_connect.js',
  '/engine/loading.js', '/engine/graph3d.js', '/engine/universe2d.js', '/engine/orb.js', '/engine/hypergraph.js', '/engine/resolve.js', '/engine/voice.js',
  '/engine/secondbrain.js', '/engine/geo_coords.js', '/engine/globe.js',
  '/engine/geosituation.js', '/engine/canvas-data.js', '/engine/command_center.js',
  '/engine/temporal-graph.js', '/nodes/temporal_seed_facts.js',
  '/nodes/temporal_seed_facts2.js', '/nodes/ontology.js', '/nodes/ontology_facts.js', '/nodes/legal_names.js',
  '/engine/timeline3d.js', '/engine/maptime.js', '/engine/khipu_lang.js', '/engine/guide.js', '/engine/xray.js', '/engine/research.js', '/engine/riskreport.js', '/engine/worldmonitor.js', '/engine/spacemonitor.js', '/engine/committee.js', '/engine/aispend.js', '/engine/pfcommittee.js', '/engine/pfreports.js', '/engine/toast.js', '/engine/sync.js', '/engine/clients.js', '/engine/mcpconnect.js', '/engine/insights.js', '/engine/statematrix.js', '/engine/livesim.js', '/engine/layers.js', '/engine/brief.js', '/engine/compare.js', '/engine/matrixview.js', '/engine/nav4.js', '/engine/khipu_chat.js', '/engine/desktop.js', '/engine/cockpit.js', '/engine/live.js', '/engine/localcharts.js', '/engine/fincard.js', '/engine/termdata.js', '/engine/explain.js', '/engine/crypto.js', '/engine/portfolios.js',
  '/nodes/crypto_intel.js', '/nodes/crypto_intel2.js',
  '/sim/scenario_builder.js',
];

const NAV_TIMEOUT_MS = 10000;
// Rutas de API: jamás al caché (datos vivos, cuenta de trading, salud del server).
const API_RE = /^\/(api|v1|mcp|oauth|\.well-known)(\/|$)/;
// CDNs inmutables (versión fijada en la URL) → cache-first.
const CDN_HOSTS = ['cdnjs.cloudflare.com', 'cdn.jsdelivr.net', 'unpkg.com',
  'fonts.googleapis.com', 'fonts.gstatic.com'];
// Clave única del shell de la app (la navegación a / o /?x=1 se guarda aquí).
const SHELL_KEY = '/';

// server.py inyecta ?v=<N de CACHE> en cada <script src="engine|nodes|sim/…">
// del shell (_versioned_app_html) → se precargan esas URLs EXACTAS.
const VER = (CACHE.match(/v(\d+)$/) || [])[1] || '';
function precacheUrl(u) {
  return (VER && /^\/(engine|nodes|sim)\/[^?]+\.js$/.test(u)) ? u + '?v=' + VER : u;
}

self.addEventListener('install', e => {
  // Precarga del shell sin fallar la instalación si algo no está. Solo se
  // guardan respuestas buenas (cache.add ya rechaza las que no son ok).
  e.waitUntil(
    caches.open(CACHE).then(c => Promise.allSettled(SHELL.map(u => c.add(precacheUrl(u)))))
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

function offlineJSON(status) {
  return new Response(JSON.stringify({
    error: 'Servidor no disponible', error_en: 'Server unavailable',
    offline: true, upstream_status: status || 0,
  }), { status: 503, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
}

function isJSON(res) {
  return (res.headers.get('content-type') || '').toLowerCase().indexOf('json') >= 0;
}

// Solo respuestas buenas y del propio origen van al caché (nunca 4xx/5xx,
// nunca redirecciones opacas).
function cacheable(res) {
  return !!res && res.ok && res.type === 'basic';
}

function put(key, res) {
  caches.open(CACHE).then(c => c.put(key, res)).catch(() => {});
}

// API: red directa, nunca caché. Red caída o página de error del proxy (≥500
// no-JSON) → JSON 503 offline:true para que la app lo entienda y lo diga.
function handleApi(req) {
  return fetch(req).then(res => {
    if (res.status >= 500 && !isJSON(res)) return offlineJSON(res.status);
    return res;
  }, () => offlineJSON(0));
}

// Cabeceras de seguridad para respuestas SINTÉTICAS (sin copia de la que
// heredarlas): la página no se puede enmarcar ni reinterpretar su tipo.
const SEC_HEADERS = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Content-Security-Policy': "frame-ancestors 'none'",
  'Referrer-Policy': 'strict-origin-when-cross-origin',
};

// Modo degradado (server caído/colgado detectado por una navegación): hasta
// este instante el código propio con copia guardada sale directo del caché.
// Vive en memoria del SW (si el navegador lo duerme, vuelve a la carrera de 8 s).
let degradedUntil = 0;
const DEGRADED_MS = 60000;
function degraded() { return Date.now() < degradedUntil; }

// Shell guardado con la marca __KHIPU_STALE_SHELL (la app muestra el aviso).
// Conserva las cabeceras de la copia guardada (CSP, frame-ancestors,
// X-Frame-Options, nosniff…): sin ellas la página de emergencia quedaba
// menos protegida que la normal.
function staleShell() {
  return caches.match(SHELL_KEY).then(m => m || caches.match('/app.html')).then(m => {
    if (!m) return null;
    return m.text().then(html => {
      const mark = '<script>window.__KHIPU_STALE_SHELL=1</script>';
      const out = /<head[^>]*>/i.test(html) ? html.replace(/<head[^>]*>/i, h => h + mark) : mark + html;
      const headers = new Headers(m.headers);
      // el cuerpo cambió (y ya viene descomprimido): fuera longitud/codificación
      ['Content-Length', 'Content-Encoding', 'Transfer-Encoding', 'ETag', 'Last-Modified'].forEach(h => headers.delete(h));
      headers.set('Content-Type', 'text/html; charset=utf-8');
      headers.set('Cache-Control', 'no-store');
      Object.keys(SEC_HEADERS).forEach(h => { if (!headers.has(h)) headers.set(h, SEC_HEADERS[h]); });
      degradedUntil = Date.now() + DEGRADED_MS;
      return new Response(out, { status: 200, headers });
    });
  }).catch(() => null);
}

function offlinePage() {
  const html = '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<title>Khipus Finance AI</title><body style="font:15px/1.5 system-ui,sans-serif;background:#0a0d14;color:#e5e7eb;padding:32px">' +
    '<h2>⚠ Servidor no disponible · Server unavailable</h2>' +
    '<p>El servidor de Khipus no responde. Reintenta en unos minutos.</p>' +
    '<p>The Khipus server is not responding. Please try again in a few minutes.</p>' +
    '<button onclick="location.reload()" style="padding:8px 16px;font-weight:700">Reintentar · Retry</button></body>';
  return new Response(html, { status: 503, headers: Object.assign({ 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' }, SEC_HEADERS) });
}

function isAppShellPath(p) {
  return p === '/' || p === '/app.html' || p === '/index.html';
}

// Navegación: red con límite de ~10 s. Si hay shell guardado y la red falla,
// tarda de más o devuelve ≥500 → shell viejo marcado. Sin shell guardado se
// espera a la red (primera visita en red lenta).
function handleNavigate(req, url) {
  const isShell = isAppShellPath(url.pathname);
  const net = fetch(req).then(res => {
    if (isShell && cacheable(res)) put(SHELL_KEY, res.clone());
    else if (!isShell && cacheable(res)) put(req, res.clone());
    return res;
  });
  const fallback = () => (isShell ? staleShell() : caches.match(req).then(m => m || null));
  return new Promise(resolve => {
    let done = false;
    const finish = r => { if (!done && r) { done = true; resolve(r); } };
    const timer = setTimeout(() => {
      fallback().then(r => { if (r) finish(r); });
    }, NAV_TIMEOUT_MS);
    net.then(res => {
      if (res.ok) degradedUntil = 0;   // el server volvió: fin del modo degradado
      if (res.status >= 500) {
        return fallback().then(r => { clearTimeout(timer); finish(r || res); });
      }
      clearTimeout(timer); finish(res);
    }, () => {
      clearTimeout(timer);
      fallback().then(r => finish(r || offlinePage()));
    });
  });
}

// Estático propio. URLs versionadas (?v=N, las pone el server en cada <script
// src>) son INMUTABLES: si esa versión exacta ya está guardada se sirve al
// instante (así el shell viejo arranca aunque el server esté colgado). El
// resto: red primero (≤8 s si hay copia guardada); al caché solo lo bueno;
// sin red, ≥500 o tiempo agotado → copia guardada. En modo degradado (el
// shell viejo acaba de servirse) la copia sale al instante.
const STATIC_TIMEOUT_MS = 8000;
function handleStatic(req, url) {
  const cached = () => caches.match(req).then(m => m || caches.match(req, { ignoreSearch: true }));
  const network = () => fetch(req).then(res => {
    if (cacheable(res)) { put(req, res.clone()); return res; }
    if (res.status >= 500) return cached().then(m => m || res);
    return res;
  }, () => cached().then(m => m || Response.error()));
  // red con límite: si no contesta en STATIC_TIMEOUT_MS → la copia guardada.
  // (Antes una URL versionada sin copia EXACTA esperaba a la red sin límite:
  // primer shell viejo tras instalar + server colgado = app en blanco y sin
  // franja roja durante minutos.)
  const raced = copy => new Promise(resolve => {
    let done = false;
    const finish = r => { if (!done) { done = true; resolve(r); } };
    const timer = setTimeout(() => finish(copy), STATIC_TIMEOUT_MS);
    network().then(r => { clearTimeout(timer); finish(r); }, () => { clearTimeout(timer); finish(copy); });
  });
  // /vendor/* = librerías con versión fijada en server.py (_VENDOR_MAP); el
  // bump de CACHE en cada despliegue las renueva → también inmutables.
  const versioned = url.searchParams.has('v') || url.pathname.indexOf('/vendor/') === 0;
  return caches.match(req).then(exact => {
    if (exact && (versioned || degraded())) return exact;
    return cached().then(copy => {
      if (!copy) return network();
      if (degraded()) return copy;
      // versión nueva aún no guardada: se prefiere la red (no mezclar
      // versiones), pero con límite; sin red, ≥500 o tiempo agotado → copia.
      return raced(copy);
    });
  });
}

// Google Fonts CSS llega opaca (<link> sin CORS): no se puede saber si es un
// error, pero un error ahí solo cambia la tipografía → se permite guardarla.
// Cualquier otra respuesta opaca (JS de CDN) NO: un 4xx/5xx guardado se
// serviría cache-first hasta el próximo bump de CACHE.
function cdnCacheable(res, url) {
  if (res.ok) return true;
  return res.type === 'opaque' && url.hostname === 'fonts.googleapis.com';
}

function handleCdn(req, url) {
  return caches.match(req).then(hit => hit || fetch(req).then(res => {
    if (cdnCacheable(res, url)) put(req, res.clone());
    return res;
  }));
}

self.addEventListener('fetch', e => {
  const req = e.request;
  let url;
  try { url = new URL(req.url); } catch (_) { return; }
  const sameOrigin = url.origin === self.location.origin;

  if (sameOrigin && API_RE.test(url.pathname)) {
    // Pantallas de consentimiento OAuth y similares, y envíos keepalive/beacon
    // (deben sobrevivir al cierre de la página): el navegador decide.
    if (req.mode === 'navigate' || req.keepalive) return;
    e.respondWith(handleApi(req));
    return;
  }
  if (req.method !== 'GET') return;

  if (sameOrigin) {
    if (req.mode === 'navigate') { e.respondWith(handleNavigate(req, url)); return; }
    if (url.pathname === '/sw.js') return;
    e.respondWith(handleStatic(req, url));
    return;
  }
  if (CDN_HOSTS.indexOf(url.hostname) >= 0) e.respondWith(handleCdn(req, url));
  // cualquier otro origen: sin intervenir
});
