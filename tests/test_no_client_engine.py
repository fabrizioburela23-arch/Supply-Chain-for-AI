"""tests/test_no_client_engine.py — INFRA_OPERATIVA paso 13 (§4.7): en el navegador NO queda ningún motor de contagio.

Cierra PROP-01/02/03/04/11/12/13, G5-03, M-code-01 y MAP 1 #9: la misma caída daba entre 164 y 315 empresas
según la pantalla (motor de estados del navegador, cascada binaria `computeDownstream`, 55 % fijo del X-Ray,
sala de guerra 4/0,85…). Ahora TODA cifra de impacto la da el kernel único del servidor por /api/hot/*, a
través de engine/hotclient.js (window.KhipuHot).

Tres niveles:
1. Estáticas (siempre): no existen las funciones ni las constantes viejas; statematrix.js no propaga; las
   pantallas leen KhipuHot; hotclient.js va al SHELL de sw.js y se carga antes que sus usuarios.
2. hotclient.js en Node (vm, fetch falso): caché por generación, revalidación con ETag (304), sin conexión /
   calentando / 'up' sin soporte → mensajes bilingües honestos y SIN cifras; 'price'/'sanction' mapeados.
3. Navegador (Playwright + Chromium, si hay) contra el servidor REAL (Flask test client, snapshot sin base):
   X-Ray, la ventana de simulación de la Cabina y la simulación en vivo muestran el MISMO número para la caída
   de TSMC, y ese número es el de matrix.engine.propagate.
"""
import json
import os
from tests._app_source import app_source  # noqa: E402
import re
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
NODE = shutil.which('node')


def _r(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


def _client_sources():
    out = {'app.html': app_source()}
    for fn in sorted(os.listdir(os.path.join(ROOT, 'engine'))):
        if fn.endswith('.js'):
            out['engine/' + fn] = _r('engine', fn)
    return out


# ═══════════════════════════════ 1) estáticas ═══════════════════════════════
def test_no_quedan_motores_de_contagio_en_el_cliente():
    bad = []
    for name, src in _client_sources().items():
        for tok in ('computeDownstream', 'clientInsights', 'clientChokepoint', 'KhipuStateCore',
                    'KhipuState.simulate', 'xrayComputeWinners', 'xrayImpactViaState', 'impactViaState',
                    'depInWeight', 'COLLAPSE_THRESHOLD', 'CRITICAL_WEIGHT'):
            if tok in src:
                bad.append((name, tok))
    assert not bad, bad


def test_statematrix_solo_anima():
    sm = _r('engine', 'statematrix.js')
    code = re.sub(r'/\*[\s\S]*?\*/|//[^\n]*', '', sm)          # sin comentarios
    for tok in ('damping', 'SOLE_LINK_FLOOR', 'REL_W', 'incoming', 'customers', 'frag', 'simulate', 'iters',
                'colSum', 'rowSum', 'LINKS'):
        assert tok not in code, tok
    assert 'frames' in code and 'baseline' in code and 'idsInSector' in code


def test_sin_cifras_inventadas_ni_parametros_propios():
    xr = _r('engine', 'xray.js')
    assert '= 55;' not in xr and 'impacts[aid]' not in xr
    app = app_source()
    assert '4, 0.85' not in app and 'salud: 0.2' not in app
    # nada de "+min(45, gains×14) %" de ganadores inventados
    for name, src in _client_sources().items():
        assert 'Math.min(45' not in src, name
    lv = _r('engine', 'livesim.js')
    assert '/api/matrix/factors' not in lv          # los factores los aplica el servidor ('active')


def test_las_pantallas_leen_el_motor_del_servidor():
    S = _client_sources()
    for name in ('engine/xray.js', 'engine/cockpit.js', 'engine/livesim.js', 'engine/voice.js',
                 'engine/secondbrain.js', 'app.html'):
        assert 'KhipuHot.simulate' in S[name] or ('const KH = window.KhipuHot' in S[name] and 'KH.simulate(' in S[name]), name
    assert 'KH.chokepoints(' in S['engine/insights.js'] and 'KH.factors()' in S['engine/insights.js']
    assert 'KH.chokepoints(' in S['engine/brief.js'] and 'KH.factors()' in S['engine/brief.js']
    assert '/api/matrix/metrics' not in S['engine/insights.js'] and '/api/matrix/metrics' not in S['engine/brief.js']
    hc = S['engine/hotclient.js']
    for route in ('/api/hot/impact/', '/api/hot/chokepoints', '/api/hot/factors', '/api/hot/scenario'):
        assert route in hc, route
    assert '/v1/' not in hc
    # cada vista dice su generación/edad donde importa
    for name in ('engine/xray.js', 'engine/cockpit.js', 'engine/livesim.js', 'engine/insights.js',
                 'engine/secondbrain.js', 'app.html'):
        assert 'stampHTML(' in S[name], name
    assert 'KH.stamp(' in S['engine/brief.js']


def test_live_js_ya_no_limpia_el_nrs_en_cada_tick():
    lv = re.sub(r'//[^\n]*', '', _r('engine', 'live.js'))
    assert '_invalidateNRS' not in lv


def test_sw_shell_y_orden_de_carga():
    sw = _r('sw.js')
    assert "'/engine/hotclient.js'" in sw
    m = re.search(r"const CACHE = 'khipu-finance-v(\d+)'", sw[:2048])
    assert m and int(m.group(1)) >= 259
    app = _r('app.html')
    pos = {f: app.index('<script src="engine/' + f + '"></script>') for f in
           ('hotclient.js', 'xray.js', 'voice.js', 'secondbrain.js', 'insights.js', 'statematrix.js', 'livesim.js',
            'brief.js', 'cockpit.js', 'live.js')}
    assert all(pos['hotclient.js'] < v for k, v in pos.items() if k != 'hotclient.js'), pos


def test_textos_nuevos_bilingues():
    hc = _r('engine', 'hotclient.js')
    for es, en in (('sin conexión', 'offline'), ('se están preparando', 'warming up'),
                   ('auge de demanda', 'Demand booms'), ('Elige al menos una empresa', 'Pick at least one company')):
        assert es in hc and en in hc, (es, en)
    app = app_source()
    assert len(re.findall(r'\bst_wait:', app)) == 2 and len(re.findall(r'\bst_err:', app)) == 2      # ES y EN
    ex = _r('engine', 'explain.js')
    assert 'impact_sum: {' in ex and "'¿Qué son" in ex and "'What are" in ex   # el "?" de las métricas nuevas


# ═══════════════════════════ 2) hotclient.js en Node ═══════════════════════════
HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const calls = [];
let online = true, mode = 'ok', gen = 'g0.rAAA.c1.snapshot';
const view = () => ({ name: 'impact', generation: gen, graph_version: 0, source: 'snapshot', age_ms: 1500, stale: false, built_at: '2026-10-13T00:00:00Z' });
function resp(status, body, headers) {
  headers = headers || {};
  return { ok: status >= 200 && status < 300, status, headers: { get: (k) => headers[k] == null ? null : headers[k] },
           json: async () => body };
}
const W = { LANG: 'es', navigator: { get onLine() { return online; } }, NODES: [
  { id: 'TSMC', cat: 'foundry' }, { id: 'Samsung', cat: 'foundry' }, { id: 'Intel', cat: 'foundry' },
  { id: 'Nvidia', cat: 'gpu' }, { id: 'AMD', cat: 'gpu' }, { id: 'Apple', cat: 'device' }],
  NODE_META: { Samsung: { mktcap_b: 300 }, Intel: { mktcap_b: 100 } } };
W.NODE_BY_ID = {}; W.NODES.forEach(n => { W.NODE_BY_ID[n.id] = n; });
W.fetch = async (url, init) => {
  init = init || {};
  calls.push([init.method || 'GET', url, (init.headers || {})['If-None-Match'] || null, init.body || null]);
  if (mode === 'throw') throw new Error('net');
  if (mode === 'sw_offline') return resp(503, { error: 'sin conexión', offline: true });
  if (mode === 'warming') return resp(503, { code: 'view_warming', retry_after: 3 });
  const tag = '"impact:' + gen + '"';
  if (url.startsWith('/api/hot/impact/')) {
    if ((init.headers || {})['If-None-Match'] === tag) return resp(304, null, { ETag: tag, 'X-Khipu-Graph-Version': '0' });
    if (url.includes('/NoExiste')) return resp(404, { error: 'id desconocido', error_en: 'unknown id', code: 'unknown_id' });
    const sev = /severity=(\d+)/.exec(url);
    const k = sev ? +sev[1] / 100 : 1;
    return resp(200, { data: { id: 'TSMC', affected: 3, reach_1: 3, reach_10: 2, sum_impact: 1.1, by_hop: { 1: 2, 2: 1 },
      victims: [{ id: 'Nvidia', pct: 60 * k, hop: 1 }, { id: 'Apple', pct: 40 * k, hop: 1 }, { id: 'AMD', pct: 10 * k, hop: 2 }] }, view: view() },
      { ETag: tag, 'X-Khipu-Graph-Version': '0' });
  }
  if (url === '/api/hot/scenario') {
    const b = JSON.parse(init.body);
    if (b.direction === 'up') return resp(400, { error: "direction 'up' todavía no", error_en: 'not yet', param: 'direction' });
    return resp(200, { data: { shocks: b.shocks, affected: 1, reach_1: 1, reach_10: 1, sum_impact: 0.5, by_hop: { 1: 1 },
      victims: [{ id: 'Apple', pct: 50, hop: 1 }] }, view: view() });
  }
  if (url.startsWith('/api/hot/chokepoints')) return resp(200, { data: { chokepoints: [{ id: 'TSMC', reach_1: 3 }] }, view: view() }, { ETag: '"c:' + gen + '"' });
  return resp(404, {});
};
W.globalThis = W; W.window = W;
vm.createContext(W);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), W);
vm.runInContext(fs.readFileSync(process.argv[3], 'utf8'), W);
const KH = W.KhipuHot, R = {};
(async () => {
  let r = await KH.simulate({ targets: ['TSMC'], kind: 'collapse' });
  R.collapse = { ok: r.ok, reach: r.reach_1, impact: [...r.impact.entries()], stamp: KH.stamp(r.view), html: KH.stampHTML(r.view) };
  R.frames = W.KhipuState.frames(r).map(f => [...f.entries()]);
  await KH.simulate({ targets: ['TSMC'], kind: 'collapse' });                  // misma petición → caché (sin red)
  R.calls_after_cache = calls.length;
  R.rivals = KH.rivals(['TSMC'], r.impact, 4);
  const p1 = KH.impact('TSMC', { severity: 50 }), p2 = KH.impact('TSMC', { severity: 50 });  // a la vez = UNA petición
  const [a, b] = await Promise.all([p1, p2]);
  R.dedup = { same: a === b, calls: calls.length };
  r = await KH.simulate({ targets: ['TSMC'], kind: 'price', severity: 50 });
  R.price = { ok: r.ok, dir: r.direction, mapped: r.mapped, note: r.note, sev: r.severity, top: r.impact.get('Nvidia') };
  r = await KH.simulate({ targets: ['TSMC', 'Samsung'], kind: 'sanction', severity: 80 });
  R.multi = { ok: r.ok, body: JSON.parse(calls[calls.length - 1][3]), seeds: [r.impact.get('TSMC'), r.impact.get('Samsung')] };
  r = await KH.simulate({ targets: ['Nvidia'], kind: 'demand', severity: 60 });
  R.up = { ok: r.ok, code: r.code, impact: r.impact === undefined, err: r.error };
  const n0 = calls.length; r = await KH.simulate({ targets: ['Nvidia'], kind: 'demand' });
  R.up_again = { code: r.code, calls: calls.length - n0 };
  W.LANG = 'en'; r = await KH.simulate({ targets: ['Nvidia'], kind: 'demand' }); R.up_en = r.error; W.LANG = 'es';
  // revalidación con ETag tras el TTL: 304 → misma respuesta, sin cuerpo
  vm.runInContext('(function(){var n=Date.now;Date.now=function(){return n()+' + (KH.TTL_MS + 5) + ';};globalThis.__restore=function(){Date.now=n;};})()', W);
  r = await KH.impact('TSMC'); W.__restore();
  R.revalidate = { ok: r.ok, inm: calls[calls.length - 1][2], rev: KH.stats().revalidated };
  // nueva generación → se olvida la caché
  gen = 'g1.rAAA.c2.snapshot'; await KH.chokepoints({ limit: 1 });
  R.flush = KH.stats().flushes; const n1 = calls.length; await KH.impact('TSMC'); R.after_flush_calls = calls.length - n1;
  // errores: id desconocido, sin conexión (navegador / service worker / red caída), calentando
  r = await KH.simulate({ targets: ['NoExiste'] }); R.unknown = [r.ok, r.code];
  online = false; KH.flush(); r = await KH.simulate({ targets: ['TSMC'] }); R.offline = [r.ok, r.code, r.error, r.impact === undefined]; online = true;
  mode = 'sw_offline'; r = await KH.impact('Intel'); R.sw_offline = r.code;
  mode = 'throw'; r = await KH.impact('Apple'); R.throw = r.code;
  mode = 'warming'; r = await KH.chokepoints({ by: 'count', limit: 3 }); W.LANG = 'en'; R.warming = [r.code, (await KH.impact('AMD')).error]; W.LANG = 'es';
  mode = 'ok'; r = await KH.simulate({ targets: [] }); R.empty = r.code;
  console.log(JSON.stringify(R));
})().catch(e => { console.log(JSON.stringify({ fatal: String(e && e.stack || e) })); });
"""


@pytest.fixture(scope='module')
def H(tmp_path_factory):
    if not NODE:
        pytest.skip('node no instalado')
    d = tmp_path_factory.mktemp('hot')
    p = d / 'h.js'
    p.write_text(HARNESS, encoding='utf-8')
    out = subprocess.run([NODE, str(p), os.path.join(ROOT, 'engine', 'hotclient.js'),
                          os.path.join(ROOT, 'engine', 'statematrix.js')],
                         capture_output=True, text=True, timeout=60, cwd=str(d))
    lines = [x for x in out.stdout.splitlines() if x.startswith('{')]
    assert lines, out.stdout + out.stderr
    res = json.loads(lines[-1])
    assert 'fatal' not in res, res
    return res


def test_simulate_devuelve_las_cifras_del_servidor_con_su_sello(H):
    c = H['collapse']
    assert c['ok'] and c['reach'] == 3
    assert c['impact'] == [['TSMC', 100], ['Nvidia', 60], ['Apple', 40], ['AMD', 10]]
    assert c['stamp'] == 'g0 · catálogo · hace 2 s'
    assert 'kh-hot-stamp' in c['html'] and 'g0.rAAA.c1.snapshot' in c['html']
    # película por salto con los `hop` del servidor (sin recalcular)
    assert H['frames'] == [[['TSMC', 100]], [['TSMC', 100], ['Nvidia', 60], ['Apple', 40]],
                           [['TSMC', 100], ['Nvidia', 60], ['Apple', 40], ['AMD', 10]]]


def test_cache_y_peticiones_unicas(H):
    assert H['calls_after_cache'] == 1                     # la segunda pantalla no vuelve a pedir
    assert H['dedup'] == {'same': True, 'calls': 2}        # dos pantallas a la vez = UNA petición


def test_rivales_sin_porcentaje_inventado(H):
    rv = H['rivals']
    # rubros con golpes ≥40 % (foundry, gpu): rivales con golpe <15 %, por capitalización (AMD: 10 % del servidor)
    assert [x['id'] for x in rv] == ['Samsung', 'Intel', 'AMD']
    assert [x['hit'] for x in rv] == [0, 0, 10]
    assert all(set(x) == {'id', 'hit', 'cat_damaged', 'cap'} for x in rv) and all('up' not in x for x in rv)


def test_tipos_mapeados_y_auge_sin_soporte_honesto(H):
    p = H['price']
    assert p['ok'] and p['dir'] == 'down' and p['mapped'] and p['sev'] == 50 and p['top'] == 30
    assert 'intensidad transmitida' in p['note']
    m = H['multi']
    assert m['ok'] and m['body']['factors'] == 'active' and m['body']['direction'] == 'down'
    assert m['body']['shocks'] == [{'id': 'TSMC', 'magnitude': 0.8}, {'id': 'Samsung', 'magnitude': 0.8}]
    assert m['seeds'] == [80, 80]
    u = H['up']
    assert u['ok'] is False and u['code'] == 'unsupported_direction' and u['impact'] is True
    assert 'No mostramos cifras inventadas' in u['err']
    assert H['up_again'] == {'code': 'unsupported_direction', 'calls': 0}   # no se martilla al servidor
    assert 'We do not show made-up figures' in H['up_en']


def test_revalidacion_etag_y_cambio_de_generacion(H):
    rv = H['revalidate']
    assert rv['ok'] and rv['inm'] == '"impact:g0.rAAA.c1.snapshot"' and rv['rev'] == 1
    assert H['flush'] >= 1 and H['after_flush_calls'] == 1


def test_errores_honestos_y_bilingues(H):
    assert H['unknown'] == [False, 'unknown_id']
    ok, code, msg, no_numbers = H['offline']
    assert ok is False and code == 'offline' and no_numbers and 'No se puede calcular sin conexión' in msg
    assert H['sw_offline'] == 'offline' and H['throw'] == 'offline'
    assert H['warming'][0] == 'view_warming' and 'warming up' in H['warming'][1]
    assert H['empty'] == 'no_targets'


# ═══════════════ 3) navegador: el MISMO número en tres pantallas (servidor real) ═══════════════
def _chromium(p):
    for kw in ({}, {'executable_path': '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', 'args': ['--no-sandbox']}):
        try:
            return p.chromium.launch(**kw)
        except Exception:  # noqa: BLE001
            continue
    return None


PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"></head><body>
<main id="mainmap" style="display:flex"><div class="graph-wrap" style="position:relative;width:900px;height:600px"></div></main>
<div id="xr" class="xr-full" style="width:600px"><div id="xr-impact"></div><div id="xr-struct"></div></div>
<script>
window.LANG = 'es';
window.NODES = __NODES__;
window.NODE_BY_ID = {}; window.NODES.forEach(function (n) { window.NODE_BY_ID[n.id] = n; });
window.NODE_META = {}; window.LINKS = []; window.SECTORS9 = __SECTORS__; window.CAT_TO_SECTOR = __CAT2SEC__;
window.computeNRS = function () { return 40; };
window.__paint = [];
window._liveRecolorByImpact = function (m, dir) { window.__paint.push([m.size, dir]); };
window._liveTintLinks = function () {};
window._liveResetColors = function () {};
window.KhipuChat = { appendUser: function () {}, appendPending: function () { return document.createElement('div'); },
  send: function () { return new Promise(function () {}); }, fillReply: function () {}, fillError: function () {},
  classify: function () { return { kind: 'brain' }; }, ensureStyles: function () {}, clear: function () {},
  noteEntity: function () {}, remember: function () {} };
</script></body></html>"""


@pytest.fixture
def server_client(monkeypatch):
    import ontology.db as odb
    import server
    from core import http as h
    from core.hotviews import builder, registry
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    registry.reset()
    builder.build_once()
    with h._rate_lock:
        h._rate_buckets.clear()
    yield server.app.test_client()
    registry.reset()
    with h._rate_lock:
        h._rate_buckets.clear()


def test_navegador_misma_caida_mismo_numero_en_tres_pantallas(server_client):
    pw = pytest.importorskip('playwright.sync_api')
    snap = json.loads(_r('data', 'grafo_v0.json'))
    nodes = [{'id': n['id'], 'label': n.get('label') or n['id'], 'cat': n.get('cat'), 'country': n.get('country'),
              'mkt': None} for n in snap['nodes']]
    page = (PAGE.replace('__NODES__', json.dumps(nodes))
            .replace('__SECTORS__', json.dumps({k: {'label': (v or {}).get('label', k), 'color': (v or {}).get('color', '#4C8DF6')}
                                                for k, v in (snap.get('sectors9') or {}).items()}))
            .replace('__CAT2SEC__', json.dumps(snap.get('cat_to_sector') or {})))
    # la verdad: el kernel del servidor (mismo que /api/hot) — alcance ≥1 % de la caída de TSMC
    truth = server_client.get('/api/hot/impact/TSMC?top=500').get_json()['data']
    from matrix import engine as E
    from core.hotviews import registry
    core = registry.generation().views['graph_core']
    direct, _order = E.propagate(core.mats, core.idx, core.ids, ["TSMC"], frag=core.frag)
    direct_reach = sum(1 for k, v in direct.items() if k != 'TSMC' and v >= 1.0)
    assert truth['reach_1'] == direct_reach > 200
    seen = []

    with pw.sync_playwright() as p:
        b = _chromium(p)
        if not b:
            pytest.skip('Chromium no disponible')
        ctx = b.new_context(viewport={'width': 1440, 'height': 900})

        def handler(route):
            req = route.request
            path = req.url[len('http://khipu.test'):]
            if path in ('', '/'):
                return route.fulfill(status=200, content_type='text/html', body=page)
            if path.startswith('/api/hot/'):
                seen.append((req.method, path.split('?')[0]))
                hdrs = {k: v for k, v in req.headers.items() if k.lower() in ('if-none-match', 'content-type')}
                r = (server_client.post(path, data=req.post_data, headers=hdrs) if req.method == 'POST'
                     else server_client.get(path, headers=hdrs))
                out = {k: v for k, v in r.headers.items() if k in ('ETag', 'X-Khipu-Graph-Version')}
                return route.fulfill(status=r.status_code, content_type='application/json', headers=out,
                                     body=r.get_data(as_text=True))
            return route.fulfill(status=503, content_type='application/json', body=json.dumps({'error': 'sin servidor'}))
        ctx.route('http://khipu.test/**', handler)
        pg = ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('http://khipu.test/')
        for f in ('toast.js', 'agents_registry.js', 'hotclient.js', 'mascot.js', 'statematrix.js', 'xray.js',
                  'livesim.js', 'desktop.js', 'cockpit.js'):
            pg.add_script_tag(content=_r('engine', f))
        # 1) X-Ray
        pg.evaluate("() => window.wireXRay(document.getElementById('xr'), 'TSMC')")
        pg.wait_for_function("() => document.querySelector('#xr .icell b')", timeout=15000)
        xr = pg.evaluate("""() => ({ reach: +document.querySelector('#xr .icell b').textContent,
            rows: [...document.querySelectorAll('#xr .xr-victim:not(.win)')].slice(0, 6).map(r => [r.querySelector('.vn').textContent, r.querySelector('.vp').textContent]),
            stamp: (document.querySelector('#xr .kh-hot-stamp') || {}).textContent || '' })""")
        # 2) Cabina: ventana de simulación
        pg.evaluate("() => { BixbyCockpit.open(); BixbyCockpit.stage('sim', { id: 'TSMC', kind: 'collapse' }); }")
        pg.wait_for_function("() => document.querySelector('.kos-sim-reach')", timeout=15000)
        ck = pg.evaluate("""() => ({ reach: +document.querySelector('.kos-sim-reach').textContent,
            rows: [...document.querySelectorAll('.bcp-two > div:first-child .bcp-row')].slice(0, 6).map(r => [r.querySelector('.nm').textContent, r.querySelector('.pv').textContent]),
            stamp: (document.querySelector('.kos-sim-stamp .kh-hot-stamp') || {}).textContent || '' })""")
        # 3) simulación en vivo del mapa (TSMC, corte al 100 %)
        pg.evaluate("() => window._lsToggle()")
        pg.wait_for_function("() => document.querySelector('#ls-stats .ls-cell b')", timeout=15000)
        ls = pg.evaluate("() => +document.querySelector('#ls-stats .ls-cell b').textContent")
        paint = pg.evaluate('() => window.__paint')
        # un auge de demanda: honesto, sin cifras
        pg.evaluate("() => { BixbyCockpit.stage('sim', { id: 'Nvidia', kind: 'demand', severity: 60 }); }")
        pg.wait_for_function("() => document.querySelector('.kos-sim-err')", timeout=15000)
        up = pg.evaluate("() => document.querySelector('.kos-sim-err').textContent")
        st = pg.evaluate('() => KhipuHot.stats()')
        ctx.close()
        b.close()
    assert not errs, errs
    assert xr['reach'] == ck['reach'] == ls == truth['reach_1'], (xr['reach'], ck['reach'], ls, truth['reach_1'])
    assert xr['rows'] == ck['rows'] and len(xr['rows']) == 6
    import math
    top = [(v['label'], str(math.floor(v['pct'] + 0.5)) + '%') for v in truth['victims'][:6]]   # Math.round de JS
    assert [tuple(x) for x in xr['rows']] == top
    assert xr['stamp'].startswith('g0 · catálogo') and ck['stamp'].startswith('g0 · catálogo')
    assert paint and paint[-1][0] == len([v for v in truth['victims']]) + 1 and paint[-1][1] == 'down'
    assert 'No mostramos cifras inventadas' in up
    # X-Ray y Cabina comparten la MISMA respuesta (caché): una sola lectura de /api/hot/impact/TSMC
    assert seen.count(('GET', '/api/hot/impact/TSMC')) == 1, seen
    assert ('POST', '/api/hot/scenario') in seen and st['hits'] >= 2
