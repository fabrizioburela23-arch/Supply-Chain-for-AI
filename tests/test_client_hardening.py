"""
tests/test_client_hardening.py — contrato de seguridad del CLIENTE (auditoría
estructural 2026-09-30, grupo CLIENT: #3 #4 #9 #10 #18 + revisión).

Ejecuta el código REAL del navegador en Node (vm) con stubs mínimos — sin
navegador ni server:
  · app.html, primer bloque inline ("Seguridad compartida del cliente"):
    _tradeOrderIsDup (contrato 200 duplicate:true del server), client_order_id
    persistente (recarga/otra pestaña), _tradeOrderResolve, PIN de 12 h,
    safeUrl, guardia de enlaces javascript:, _tradeStatusInfo (paper sin PIN),
    franja "servidor no disponible" con el shell viejo.
  · sw.js: precarga de URLs ?v=N exactas, carrera con límite para versionadas
    sin copia exacta (server colgado tras instalar), shell viejo con las
    cabeceras de seguridad de la copia, modo degradado, API nunca cacheada,
    CDN: solo respuestas buenas (opaca solo la CSS de Google Fonts).
Se salta si no hay `node` (≥18: Response/Headers globales).
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(not NODE, reason='node no instalado')


def _client_block():
    html = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    start = html.index('/* ── Seguridad compartida del cliente')
    end = html.index('</script>', start)
    return html[start:end]


def _run_node(script, payload):
    """Corre `script` en Node con PAYLOAD (json) en stdin; devuelve su JSON."""
    p = subprocess.run([NODE, '-e', script], input=json.dumps(payload), capture_output=True,
                       text=True, timeout=60)
    assert p.returncode == 0, p.stderr[-2000:]
    return json.loads(p.stdout.strip().splitlines()[-1])


# ─────────────────────────────── app.html ────────────────────────────────────
APP_HARNESS = r'''
const vm = require('vm');
const P = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const SRC = P.src;
function mkLS(store) {
  return { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); },
           removeItem: k => { delete store[k]; } };
}
function mkEl(tag) {
  return { tag, id: '', style: {}, innerHTML: '', attrs: {}, setAttribute(k, v) { this.attrs[k] = v; } };
}
function boot(store, opts) {
  opts = opts || {};
  const listeners = {};
  const appended = [];
  let fetchCalls = 0;
  const body = { appendChild: el => { appended.push(el); } };
  const document = {
    body, addEventListener: (t, f) => { (listeners[t] = listeners[t] || []).push(f); },
    createElement: mkEl,
    getElementById: id => appended.find(e => e.id === id) || (id === 'srv-retry' ? {} : null),
  };
  const ctx = {
    localStorage: mkLS(store), document, location: { href: 'https://app.example/' }, URL,
    setTimeout, clearTimeout, console, Uint8Array, crypto: require('crypto').webcrypto,
    AbortController, Response, Headers,
    fetch: async (url) => { fetchCalls++; return opts.fetch ? opts.fetch(url) : Promise.reject(new Error('offline')); },
    LANG: opts.lang, __KHIPU_STALE_SHELL: opts.stale ? 1 : undefined, BASE: '',
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return { w: ctx, listeners, appended, fetches: () => fetchCalls };
}
(async () => {
  const out = {};
  // 1) duplicado: contrato real del server (200 + duplicate:true) y 422 de respaldo
  let { w } = boot({});
  out.dup = {
    ok200dup: w._tradeOrderIsDup(200, { id: 'a', status: 'accepted', duplicate: true }),
    ok200new: w._tradeOrderIsDup(200, { id: 'a', status: 'accepted' }),
    ok200false: w._tradeOrderIsDup(200, { id: 'a', duplicate: 'yes' }),
    r422dup: w._tradeOrderIsDup(422, { code: 'broker_rejected', message: 'client_order_id must be unique' }),
    r422other: w._tradeOrderIsDup(422, { message: 'insufficient buying power' }),
    r502: w._tradeOrderIsDup(502, { client_order_id: 'x', code: 'broker_unreachable' }),
  };
  // 2) client_order_id persistente: ambiguo → recarga → mismo id; resuelto → id nuevo
  const store = {};
  let a = boot(store).w;
  const sig = 'panel|AAPL|buy|limit|1|100|day';
  const id1 = a._tradeOrderId(sig);
  const idSame = a._tradeOrderId(sig);
  a._tradeOrderSettle(sig, true);
  let b = boot(store).w;                               // "recarga" / otra pestaña
  const idAfterReload = b._tradeOrderId(sig);
  const resolved = b._tradeOrderResolve(sig, [{ client_order_id: 'zzz' }, { client_order_id: id1, status: 'accepted' }]);
  const idAfterResolve = b._tradeOrderId(sig);         // resolver NO olvida el id
  b._tradeOrderSettle(sig, false);                     // duplicado / aceptada → olvidar
  const storeAfter = store.khipu_coid_pending || null;
  const idNew = boot(store).w._tradeOrderId(sig);
  out.coid = { id1, idSame, idAfterReload, resolvedStatus: resolved && resolved.status, idAfterResolve,
               storeAfter, idNew, uuid: /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(id1) };
  // 2b) caducidad (24 h) y tope de entradas
  const old = { khipu_coid_pending: JSON.stringify({ s: { id: 'old-id-123', ts: Date.now() - 25 * 3600e3 } }) };
  out.coidTTL = boot(old).w._tradeOrderId('s') !== 'old-id-123';
  const many = {}; const m = boot(many).w;
  for (let i = 0; i < 60; i++) m._tradeOrderId('sig' + i);
  out.coidMax = Object.keys(JSON.parse(many.khipu_coid_pending)).length;
  const bad = { khipu_coid_pending: '{not json' };
  out.coidBadJson = typeof boot(bad).w._tradeOrderId('x') === 'string';
  // otra pestaña resolvió la orden (clave borrada) → esta pestaña NO la resucita
  const shared = {}; const tA = boot(shared).w, tB = boot(shared).w;
  const idA = tA._tradeOrderId('s2'); tA._tradeOrderSettle('s2', true);
  tB._tradeOrderSettle('s2', false);
  out.coidCrossTab = tA._tradeOrderId('s2') !== idA;
  // localStorage que falla al escribir (cuota/privado) → sigue en memoria
  const q = boot({}).w;
  q.localStorage.setItem = () => { throw new Error('QuotaExceededError'); };
  const iq = q._tradeOrderId('s3'); q._tradeOrderSettle('s3', true);
  out.coidQuota = q._tradeOrderId('s3') === iq;
  // 3) PIN 12 h
  const ps = {}; const pw = boot(ps).w;
  pw._tradePinSave('4321');
  out.pin = { saved: pw._tradePinStored(), ttlH: (+ps.khipu_trade_pin_exp - Date.now()) / 3600e3 };
  ps.khipu_trade_pin_exp = String(Date.now() - 1000);
  out.pin.expired = pw._tradePinStored();
  out.pin.clearedKey = ps.khipu_trade_pin === undefined;
  const legacy = { khipu_trade_pin: '777' }; const lw = boot(legacy).w;
  out.pin.legacy = lw._tradePinStored();
  out.pin.legacyExpSet = +legacy.khipu_trade_pin_exp > Date.now();
  // 4) safeUrl
  w = boot({}).w;
  out.safe = { js: w.safeUrl('javascript:alert(1)'), jsTab: w.safeUrl('java\tscript:alert(1)'),
               vb: w.safeUrl('vbscript:x'), data: w.safeUrl('data:text/html,x'), empty: w.safeUrl(''),
               https: w.safeUrl('https://ex.com/a?b=1&c="x\'y') };
  // 5) guardia de enlaces (clic capturado en document)
  const g = boot({});
  const click = (href, extra) => {
    let prevented = false;
    const a2 = Object.assign({ nodeType: 1, localName: 'a', parentNode: null,
      getAttribute: k => (k === 'href' ? href : null), hasAttribute: k => !!(extra && extra[k]) }, {});
    const inner = { nodeType: 1, localName: 'span', parentNode: a2 };
    g.listeners.click.forEach(f => f({ target: inner, preventDefault() { prevented = true; }, stopImmediatePropagation() {} }));
    return prevented;
  };
  out.guard = { js: click('java\tscript:alert(1)'), jsUpper: click('  JAVASCRIPT:x'), vb: click('vbscript:x'),
                https: click('https://ex.com'), rel: click('#tab'), dataDownload: click('data:text/csv,a', { download: true }),
                dataNav: click('data:text/html,x'), aux: !!(g.listeners.auxclick && g.listeners.auxclick.length) };
  // 6) /api/trade/status público → {pin_set, paper} (badge sin PIN), con caché
  const st = boot({}, { fetch: async () => ({ ok: true, json: async () => ({ pin_set: true, paper: false }) }) });
  const s1 = await st.w._tradeStatusInfo();
  const req = await st.w._tradePinRequired();
  out.status = { s1, req, fetches: st.fetches() };
  // 6b) sin PIN y server que lo exige → 401 sintético SIN tocar /api/trade/order
  const sy = boot({}, { fetch: async (u) => (/trade\/status/.test(u) ? { ok: true, json: async () => ({ pin_set: true, paper: true }) } : { status: 200, ok: true }) });
  const r = await sy.w._tradeFetch('/api/trade/order', { method: 'POST' }, false);
  out.synth = { status: r.status, code: (await r.json()).code, fetches: sy.fetches() };
  // 7) franja con el shell viejo del SW: se pinta al instante (ES/EN)
  const bs = boot({}, { stale: true });
  const bn = bs.appended.find(e => e.id === 'srv-down');
  const be = boot({}, { stale: true, lang: 'en' }).appended.find(e => e.id === 'srv-down');
  const bnone = boot({}).appended.find(e => e.id === 'srv-down');
  out.banner = { es: !!bn && /servidor de Khipus no responde/.test(bn.innerHTML) && bn.style.display === 'flex',
                 en: !!be && /server is not responding/.test(be.innerHTML), notWithoutFlag: !bnone };
  console.log(JSON.stringify(out));
})().catch(e => { console.error(e && e.stack || e); process.exit(1); });
'''


@pytest.fixture(scope='module')
def app_res():
    return _run_node(APP_HARNESS, {'src': _client_block()})


def test_duplicate_contract_matches_server(app_res):
    d = app_res['dup']
    # server.py trade_order: 422 "client_order_id must be unique" → 200 + duplicate:true
    assert d['ok200dup'] is True
    assert d['ok200new'] is False and d['ok200false'] is False
    assert d['r422dup'] is True and d['r422other'] is False
    assert d['r502'] is False          # 502 = ambiguo, no duplicado


def test_client_order_id_survives_reload(app_res):
    c = app_res['coid']
    assert c['uuid']
    assert c['id1'] == c['idSame'] == c['idAfterReload']
    assert c['resolvedStatus'] == 'accepted'
    assert c['idAfterResolve'] == c['id1']       # ver la orden en el historial no libera el id
    assert c['storeAfter'] is None               # settle(false) lo olvida (y limpia la clave)
    assert c['idNew'] != c['id1']                # la siguiente orden igual es NUEVA
    assert app_res['coidTTL'] is True
    assert app_res['coidMax'] == 50
    assert app_res['coidBadJson'] is True
    assert app_res['coidCrossTab'] is True
    assert app_res['coidQuota'] is True


def test_pin_12h_expiry(app_res):
    p = app_res['pin']
    assert p['saved'] == '4321' and 11.9 < p['ttlH'] <= 12.0
    assert p['expired'] == '' and p['clearedKey'] is True
    assert p['legacy'] == '777' and p['legacyExpSet'] is True


def test_safe_url(app_res):
    s = app_res['safe']
    assert s['js'] == s['jsTab'] == s['vb'] == s['data'] == s['empty'] == '#'
    assert s['https'].startswith('https://ex.com/a?b=1&amp;c=')
    assert '"' not in s['https'] and "'" not in s['https']


def test_link_guard_blocks_dangerous_schemes(app_res):
    g = app_res['guard']
    assert g['js'] and g['jsUpper'] and g['vb'] and g['dataNav']
    assert not g['https'] and not g['rel'] and not g['dataDownload']
    assert g['aux']


def test_trade_status_gives_paper_without_pin(app_res):
    s = app_res['status']
    assert s['s1'] == {'pin_set': True, 'paper': False}
    assert s['req'] is True
    assert s['fetches'] == 1                     # caché: una sola llamada a /api/trade/status
    y = app_res['synth']
    assert y['status'] == 401 and y['code'] == 'pin_required'
    assert y['fetches'] == 1                     # solo /api/trade/status; la orden NO salió


def test_stale_shell_banner_first_block(app_res):
    b = app_res['banner']
    assert b['es'] and b['en'] and b['notWithoutFlag']


def test_trade_panel_checks_duplicate_before_success():
    """El panel, la voz y cripto miran el duplicado ANTES del éxito (un 200
    con duplicate:true trae id/status y antes se anunciaba como orden nueva)."""
    html = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    i = html.index('window.submitTradePanelOrder = async function')
    body = html[i:html.index('async function _tpLoadAccount', i)]
    assert body.index('_tradeOrderIsDup(st, d)') < body.index('r.ok && d && (d.id || d.status)')
    voice = open(os.path.join(ROOT, 'engine', 'voice.js'), encoding='utf-8').read()
    j = voice.index('window._executeTradeOrder = async function')
    vb = voice[j:voice.index('window._openBrokerStage', j)]
    assert vb.index('_tradeOrderIsDup') < vb.index('r.ok && d && (d.id || d.status)')
    assert 'broker_dup: true' in vb
    crypto = open(os.path.join(ROOT, 'engine', 'crypto.js'), encoding='utf-8').read()
    k = crypto.index('function tradeSend()')
    cb = crypto[k:crypto.index('function computeInsights', k)]
    assert cb.index('if (dup)') < cb.index('x.r.ok && d && (d.id')


def test_datalayer_health_has_timeout():
    html = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    i = html.index('async health(){')
    body = html[i:html.index('async _json(', i)]
    assert 'AbortController' in body and 'signal' in body and '6000' in body


# ──────────────────────────────── sw.js ──────────────────────────────────────
SW_HARNESS = r'''
const vm = require('vm');
const P = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const ORIGIN = 'https://app.example';
let src = P.src.replace(/const STATIC_TIMEOUT_MS = \d+;/, 'const STATIC_TIMEOUT_MS = 60;')
               .replace(/const NAV_TIMEOUT_MS = \d+;/, 'const NAV_TIMEOUT_MS = 80;');
const abs = u => new URL(typeof u === 'string' ? u : u.url, ORIGIN + '/').href;
function mkCaches() {
  const stores = {};
  const store = n => (stores[n] = stores[n] || new Map());
  const api = {
    added: [],
    open: async n => ({
      put: async (k, r) => { store(n).set(abs(k), r); },
      add: async u => { api.added.push(u); const r = await api.net(u); if (!r.ok) throw new Error('bad'); store(n).set(abs(u), r); },
      keys: async () => [...store(n).keys()],
    }),
    keys: async () => Object.keys(stores),
    delete: async n => delete stores[n],
    match: async (req, opts) => {
      const k = abs(req);
      for (const s of Object.values(stores)) {
        if (s.has(k)) return s.get(k).clone();
        if (opts && opts.ignoreSearch) {
          const bare = k.split('?')[0];
          for (const [kk, v] of s) if (kk.split('?')[0] === bare) return v.clone();
        }
      }
      return undefined;
    },
    net: null,
  };
  return api;
}
function resp(body, init, type) {
  const r = new Response(body, init);
  const t = type || 'basic';
  const wrap = x => { Object.defineProperty(x, 'type', { value: t }); const c = x.clone.bind(x); x.clone = () => wrap(c()); return x; };
  return wrap(r);
}
function opaque() {
  const r = new Response('');
  Object.defineProperty(r, 'type', { value: 'opaque' });
  Object.defineProperty(r, 'status', { value: 0 });
  Object.defineProperty(r, 'ok', { value: false });
  const c = r.clone.bind(r); r.clone = () => { const x = c(); Object.defineProperty(x, 'type', { value: 'opaque' }); return x; };
  return r;
}
function boot(net) {
  const listeners = {};
  const caches = mkCaches();
  let fetches = [];
  caches.net = u => net(u);
  const self = { location: new URL(ORIGIN + '/sw.js'), addEventListener: (t, f) => { listeners[t] = f; },
                 skipWaiting: () => Promise.resolve(), clients: { claim: () => Promise.resolve() } };
  const ctx = { self, caches, Response, Headers, URL, setTimeout, clearTimeout, Promise, console,
                fetch: req => { fetches.push(typeof req === 'string' ? req : req.url); return net(req); } };
  vm.createContext(ctx);
  vm.runInContext(src, ctx);
  const dispatch = (url, mode, method) => new Promise((resolve, reject) => {
    const req = { url: abs(url), mode: mode || 'cors', method: method || 'GET', keepalive: false };
    let responded = false;
    listeners.fetch({ request: req, respondWith: p => { responded = true; Promise.resolve(p).then(resolve, reject); } });
    if (!responded) resolve(null);
  });
  return { listeners, caches, ctx, dispatch, fetches: () => fetches, clearFetches: () => { fetches = []; } };
}
const hang = () => new Promise(() => {});
const SHELL_HTML = '<!doctype html><html><head><meta charset="utf-8"></head><body>app</body></html>';
const SEC = { 'Content-Type': 'text/html; charset=utf-8', 'Content-Length': String(SHELL_HTML.length),
  'Content-Security-Policy': "default-src 'self'; frame-ancestors 'none'", 'X-Frame-Options': 'DENY',
  'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-cache' };
(async () => {
  const out = {};
  const VER = (P.src.match(/khipu-finance-v(\d+)/) || [])[1];
  out.ver = VER;
  // ── install: precarga ?v=N exactas para engine/nodes/sim ──
  let mode = 'up';
  const net = req => {
    const u = typeof req === 'string' ? req : req.url;
    if (mode === 'hang') return hang();
    if (mode === 'down') return Promise.reject(new TypeError('Failed to fetch'));
    if (mode === '502html') return Promise.resolve(resp('<html>Application failed</html>', { status: 502, headers: { 'Content-Type': 'text/html' } }));
    if (new URL(abs(u)).pathname === '/') return Promise.resolve(resp(SHELL_HTML, { status: 200, headers: SEC }));
    if (/fonts\.googleapis\.com/.test(u)) return Promise.resolve(opaque());
    if (/cdnjs\.cloudflare\.com\/bad/.test(u)) return Promise.resolve(opaque());
    if (/cdn\.jsdelivr\.net\/good/.test(u)) return Promise.resolve(resp('ok', { status: 200 }, 'cors'));
    if (/\/api\//.test(u)) return Promise.resolve(resp('{"server":true}', { status: 200, headers: { 'Content-Type': 'application/json' } }));
    return Promise.resolve(resp('/*js ' + u + '*/', { status: 200, headers: { 'Content-Type': 'application/javascript' } }));
  };
  const sw = boot(net);
  await new Promise(r => sw.listeners.install({ waitUntil: p => p.then(r, r) }));
  const added = sw.caches.added;
  const eng = added.filter(u => /^\/(engine|nodes|sim)\//.test(u));
  out.precache = { n: eng.length, allVersioned: eng.every(u => u.endsWith('?v=' + VER)),
                   rootPlain: added.includes('/'), vendorPlain: added.includes('/vendor/d3.min.js') };
  // ── API nunca en caché; 502 HTML → 503 JSON offline ──
  mode = '502html';
  let r = await sw.dispatch('/api/health');
  out.api502 = { status: r.status, cc: r.headers.get('cache-control'), j: await r.json() };
  mode = 'down';
  r = await sw.dispatch('/api/trade/order', 'cors', 'POST');
  out.apiDown = { status: r.status, offline: (await r.json()).offline };
  mode = 'up';
  await sw.dispatch('/api/health');
  await new Promise(res => setTimeout(res, 20));
  out.apiCached = [];
  for (const n of await sw.caches.keys()) out.apiCached.push(...(await (await sw.caches.open(n)).keys()).filter(k => /\/api\//.test(k)));
  // ── versionada SIN copia exacta (otra ?v= guardada) + server colgado → copia tras el límite ──
  mode = 'up';
  await (await sw.caches.open('khipu-finance-v' + VER)).put('/engine/extra.js?v=1', resp('old-copy', { status: 200 }));
  mode = 'hang';
  let t0 = Date.now();
  r = await Promise.race([sw.dispatch('/engine/extra.js?v=' + VER), new Promise(res => setTimeout(() => res('TIMEOUT'), 2000))]);
  out.versionedRace = { text: r === 'TIMEOUT' ? r : await r.text(), ms: Date.now() - t0 };
  // ── navegación con server colgado → shell viejo con las cabeceras de seguridad ──
  await (await sw.caches.open('khipu-finance-v' + VER)).put('/', resp(SHELL_HTML, { status: 200, headers: SEC }));
  t0 = Date.now();
  r = await sw.dispatch('/', 'navigate');
  const html = await r.text();
  out.stale = { ms: Date.now() - t0, status: r.status, mark: html.includes('window.__KHIPU_STALE_SHELL=1'),
                markInHead: /<head[^>]*><script>window.__KHIPU_STALE_SHELL=1<\/script>/.test(html),
                csp: r.headers.get('content-security-policy'), xfo: r.headers.get('x-frame-options'),
                nosniff: r.headers.get('x-content-type-options'), cc: r.headers.get('cache-control'),
                cl: r.headers.get('content-length') };
  // ── modo degradado: estático con copia → al instante, sin esperar a la red ──
  sw.clearFetches();
  t0 = Date.now();
  r = await Promise.race([sw.dispatch('/engine/voice.js'), new Promise(res => setTimeout(() => res('TIMEOUT'), 40))]);
  out.degraded = { immediate: r !== 'TIMEOUT', ms: Date.now() - t0, fetched: sw.fetches().length };
  // ── sin red y sin shell → página offline con cabeceras de seguridad ──
  const sw2 = boot(() => Promise.reject(new TypeError('x')));
  r = await sw2.dispatch('/', 'navigate');
  out.offlinePage = { status: r.status, xfo: r.headers.get('x-frame-options'), csp: r.headers.get('content-security-policy'),
                      bilingual: /Servidor no disponible/.test(await r.text()) };
  // ── CDN: solo lo bueno (opaca solo la CSS de Google Fonts) ──
  mode = 'up';
  await sw.dispatch('https://cdnjs.cloudflare.com/bad/lib.js', 'no-cors');
  await sw.dispatch('https://fonts.googleapis.com/css2?family=X', 'no-cors');
  await sw.dispatch('https://cdn.jsdelivr.net/good/lib.js', 'cors');
  await new Promise(res => setTimeout(res, 20));
  out.cdn = { badOpaqueCached: !!(await sw.caches.match('https://cdnjs.cloudflare.com/bad/lib.js')),
              fontsCached: !!(await sw.caches.match('https://fonts.googleapis.com/css2?family=X')),
              goodCached: !!(await sw.caches.match('https://cdn.jsdelivr.net/good/lib.js')) };
  console.log(JSON.stringify(out));
  process.exit(0);
})().catch(e => { console.error(e && e.stack || e); process.exit(1); });
'''


@pytest.fixture(scope='module')
def sw_res():
    src = open(os.path.join(ROOT, 'sw.js'), encoding='utf-8').read()
    return _run_node(SW_HARNESS, {'src': src})


def test_sw_precaches_exact_versioned_urls(sw_res):
    p = sw_res['precache']
    assert sw_res['ver'] and p['n'] > 50 and p['allVersioned']
    assert p['rootPlain'] and p['vendorPlain']


def test_sw_api_never_cached_and_offline_json(sw_res):
    a = sw_res['api502']
    assert a['status'] == 503 and a['cc'] == 'no-store'
    assert a['j']['offline'] is True and a['j']['error'] and a['j']['error_en']
    assert sw_res['apiDown'] == {'status': 503, 'offline': True}
    assert not sw_res['apiCached']


def test_sw_versioned_without_exact_copy_is_bounded(sw_res):
    v = sw_res['versionedRace']
    assert v['text'] == 'old-copy', v          # antes: esperaba a la red para siempre
    assert v['ms'] < 1000


def test_sw_stale_shell_keeps_security_headers(sw_res):
    s = sw_res['stale']
    assert s['status'] == 200 and s['mark'] and s['markInHead']
    # la CSP COMPLETA de la copia guardada (no solo el respaldo frame-ancestors)
    assert "default-src 'self'" in (s['csp'] or '') and "frame-ancestors 'none'" in (s['csp'] or '')
    assert s['xfo'] == 'DENY' and s['nosniff'] == 'nosniff'
    assert s['cc'] == 'no-store' and s['cl'] is None


def test_sw_degraded_mode_serves_cache_immediately(sw_res):
    d = sw_res['degraded']
    assert d['immediate'] and d['fetched'] == 0


def test_sw_offline_page_has_security_headers(sw_res):
    o = sw_res['offlinePage']
    assert o['status'] == 503 and o['xfo'] == 'DENY' and "frame-ancestors 'none'" in o['csp'] and o['bilingual']


def test_sw_cdn_caches_only_good_responses(sw_res):
    c = sw_res['cdn']
    assert c['goodCached'] and c['fontsCached'] and not c['badOpaqueCached']


def test_sw_cache_version_readable_by_server():
    """server.py (_sw_version) lee SOLO los primeros 2048 caracteres de sw.js
    para inyectar ?v=N; un comentario largo delante de CACHE lo rompía en
    silencio (?v=0 en todos los scripts → la precarga ?v=N no coincide)."""
    import server
    sw = open(os.path.join(ROOT, 'sw.js'), encoding='utf-8').read()
    ver = re.search(r"const CACHE = 'khipu-finance-v(\d+)'", sw).group(1)
    assert server._sw_version() == ver
    assert sw.splitlines()[5].startswith("const CACHE = 'khipu-finance-v")   # línea 6 (CLAUDE.md)


def test_sw_shell_list_matches_app_scripts():
    """SHELL de sw.js = los <script src> de app.html (si no, la precarga
    ?v=N no cubre un script y el shell viejo esperaría a la red por él)."""
    html = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    sw = open(os.path.join(ROOT, 'sw.js'), encoding='utf-8').read()
    srcs = {('/' + s.lstrip('/')).split('?')[0] for s in re.findall(r'<script src="([^"]+)"', html)}
    shell = set(re.findall(r"'(/[^']+\.js)'", sw[sw.index('const SHELL'):sw.index('];', sw.index('const SHELL'))]))
    assert srcs - shell == set(), srcs - shell
