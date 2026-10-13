"""tests/test_scenario_pnl_browser.py — la línea "Tu cartera: −X ± Y USD" en el navegador (batch I3), Chromium real
contra el servidor real (Flask test client, snapshot sin base):

  · X-Ray, ventana de simulación de la Cabina y simulación en vivo muestran UNA línea discreta SOLO si hay posiciones;
  · hoy (calibración débil) la línea dice que NO hay cifra, en español y en inglés, con su «?»;
  · con una calibración que pasara las reglas, la cifra mostrada es la del SERVIDOR (−κ·Σ usd·impacto ± banda);
  · sin posiciones no aparece nada; a 1440 y 390 px la línea no desborda.
Se salta si no hay Playwright/Chromium. Capturas en $KH_SHOTS (opcional) para revisarlas a ojo.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _r(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


def _chromium(p):
    for kw in ({}, {'executable_path': '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', 'args': ['--no-sandbox']}):
        try:
            return p.chromium.launch(**kw)
        except Exception:  # noqa: BLE001
            continue
    return None


PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0;background:#0b1020;color:#e8edfb">
<main id="mainmap" style="display:flex"><div class="graph-wrap" style="position:relative;width:100%;height:300px"></div></main>
<div id="xr" class="xr-full" style="max-width:600px;padding:0 8px"><div id="xr-impact"></div><div id="xr-struct"></div></div>
<script>
window.LANG = '__LANG__';
try { localStorage.setItem('eco_lang', '__LANG__'); } catch (e) {}
window.NODES = __NODES__;
window.NODE_BY_ID = {}; window.NODES.forEach(function (n) { window.NODE_BY_ID[n.id] = n; });
window.NODE_META = {}; window.LINKS = []; window.SECTORS9 = __SECTORS__; window.CAT_TO_SECTOR = __CAT2SEC__;
window.MKT = { pos: __POS__, quotes: { NVDA: { close: 180, src: 'yahoo', as_of: '2026-10-13T15:00:00Z' },
                                       AAPL: { close: 250, live: 251, src: 'finnhub', as_of: '2026-10-13T15:00:00Z' } } };
window.quotePx = function (q) { if (!q) return 0; var v = typeof q.live === 'number' ? q.live : q.close; return Number(v) || 0; };
window.computeNRS = function () { return 40; };
window._liveRecolorByImpact = function () {}; window._liveTintLinks = function () {}; window._liveResetColors = function () {};
window.KhipuChat = { appendUser: function () {}, appendPending: function () { return document.createElement('div'); },
  send: function () { return new Promise(function () {}); }, fillReply: function () {}, fillError: function () {},
  classify: function () { return { kind: 'brain' }; }, ensureStyles: function () {}, clear: function () {},
  noteEntity: function () {}, remember: function () {} };
</script></body></html>"""

POS = {'Nvidia': {'sh': 10, 'bp': 100}, 'Apple': {'sh': 4, 'bp': 200}}


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


def _page(lang, pos):
    snap = json.loads(_r('data', 'grafo_v0.json'))
    nodes = [{'id': n['id'], 'label': n.get('label') or n['id'], 'cat': n.get('cat'), 'country': n.get('country'),
              'mkt': n.get('mkt')} for n in snap['nodes']]
    return (PAGE.replace('__NODES__', json.dumps(nodes)).replace('__LANG__', lang).replace('__POS__', json.dumps(pos))
            .replace('__SECTORS__', json.dumps({k: {'label': (v or {}).get('label', k), 'color': (v or {}).get('color', '#4C8DF6')}
                                                for k, v in (snap.get('sectors9') or {}).items()}))
            .replace('__CAT2SEC__', json.dumps(snap.get('cat_to_sector') or {})))


def _run(server_client, lang='es', width=1440, pos=POS, shots=None):
    pw = pytest.importorskip('playwright.sync_api')
    seen = []
    with pw.sync_playwright() as p:
        b = _chromium(p)
        if not b:
            pytest.skip('Chromium no disponible')
        ctx = b.new_context(viewport={'width': width, 'height': 900})
        page = _page(lang, pos)

        def handler(route):
            req = route.request
            path = req.url[len('http://khipu.test'):]
            if path in ('', '/'):
                return route.fulfill(status=200, content_type='text/html', body=page)
            if path.startswith('/api/hot/'):
                seen.append((req.method, path.split('?')[0], req.post_data))
                hdrs = {k: v for k, v in req.headers.items() if k.lower() in ('if-none-match', 'content-type')}
                r = (server_client.post(path, data=req.post_data, headers=hdrs) if req.method == 'POST'
                     else server_client.get(path, headers=hdrs))
                out = {k: v for k, v in r.headers.items() if k in ('ETag', 'X-Khipu-Graph-Version')}
                return route.fulfill(status=r.status_code, content_type='application/json', headers=out,
                                     body=r.get_data(as_text=True))
            return route.fulfill(status=503, content_type='application/json', body=json.dumps({'error': 'x'}))
        ctx.route('http://khipu.test/**', handler)
        pg = ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto('http://khipu.test/')
        for f in ('toast.js', 'explain.js', 'agents_registry.js', 'hotclient.js', 'mascot.js', 'statematrix.js',
                  'xray.js', 'livesim.js', 'desktop.js', 'cockpit.js'):
            pg.add_script_tag(content=_r('engine', f))
        out = {}
        pg.evaluate("() => window.wireXRay(document.getElementById('xr'), 'TSMC')")
        pg.wait_for_function("() => document.querySelector('#xr .icell b')", timeout=15000)
        if pos:
            pg.wait_for_function("() => { const e = document.querySelector('#xr .xr-pnl'); return e && e.textContent; }",
                                 timeout=15000)
        else:
            pg.wait_for_timeout(600)
        out['xray'] = pg.evaluate("""() => { const e = document.querySelector('#xr .xr-pnl');
            return e ? { text: e.textContent, shown: e.style.display !== 'none', chip: !!e.querySelector('span[onclick*=scenario_pnl]'),
                         overflow: e.scrollWidth > e.clientWidth + 1 } : null; }""")
        if shots:
            pg.screenshot(path=os.path.join(shots, f'xray_{lang}_{width}.png'), full_page=False)
        pg.evaluate("() => { BixbyCockpit.open(); BixbyCockpit.stage('sim', { id: 'TSMC', kind: 'collapse' }); }")
        pg.wait_for_function("() => document.querySelector('.kos-sim-reach')", timeout=15000)
        if pos:
            pg.wait_for_function("() => { const e = document.querySelector('.kos-sim-pnl'); return e && e.textContent; }",
                                 timeout=15000)
        out['cabina'] = pg.evaluate("""() => { const e = document.querySelector('.kos-sim-pnl');
            return e ? { text: e.textContent, shown: e.style.display !== 'none' } : null; }""")
        if shots:
            pg.screenshot(path=os.path.join(shots, f'cabina_{lang}_{width}.png'), full_page=False)
        pg.evaluate("() => window._lsToggle()")
        pg.wait_for_function("() => document.querySelector('#ls-stats .ls-cell b')", timeout=15000)
        if pos:
            pg.wait_for_function("() => { const e = document.getElementById('ls-pnl'); return e && e.textContent; }",
                                 timeout=15000)
        out['livesim'] = pg.evaluate("""() => { const e = document.getElementById('ls-pnl');
            return e ? { text: e.textContent, shown: e.style.display !== 'none' } : null; }""")
        ctx.close()
        b.close()
    assert not errs, errs
    out['seen'] = seen
    return out


def test_linea_honesta_sin_cifra_es_en_1440_y_390(server_client):
    shots = os.environ.get('KH_SHOTS')
    for lang, width, want in (('es', 1440, 'Tu cartera: sin cifra en dinero'), ('en', 1440, 'Your portfolio: no money figure'),
                              ('es', 390, 'Tu cartera: sin cifra en dinero'), ('en', 390, 'Your portfolio: no money figure')):
        out = _run(server_client, lang, width, shots=shots)
        for k in ('xray', 'cabina', 'livesim'):
            assert out[k] and out[k]['shown'] and out[k]['text'].startswith(want), (lang, width, k, out[k])
            assert 'USD' not in out[k]['text']                      # débil → ningún número en dinero
        assert out['xray']['chip'] and not out['xray']['overflow']
        bodies = [json.loads(s[2]) for s in out['seen'] if s[1] == '/api/hot/scenario_pnl']
        assert len(bodies) == 3
        x = bodies[0]
        assert x['record'] is False and x['shocks'] == [{'id': 'TSMC', 'magnitude': 1}]   # X-Ray: vista automática
        assert sorted(p['id'] for p in x['positions']) == ['Apple', 'Nvidia']
        assert {p['id']: p['usd'] for p in x['positions']} == {'Nvidia': 1800, 'Apple': 1004}
        # revisión lote I: Cabina / en vivo tampoco dejan ficha desde la línea de dinero (la de la simulación sale de
        # UN sitio: /api/hot/scenario con 2+ semillas); antes, con posiciones, había DOS whatif.shock por ajuste
        assert bodies[1]['record'] is False and bodies[2]['record'] is False


def test_con_calibracion_que_pasa_las_reglas_la_cifra_es_la_del_servidor(server_client, monkeypatch):
    from core import scenario_pnl as SP
    cal = {'kernel_params_semver': '1.0.0', 'rules': {'band_z': 1.645}, 'status': 'proposed', 'episodes': [],
           'fit': {'status': 'ok', 'kappa': 0.2, 'kappa_se': 0.05, 'resid_sd': 0.1, 'n': 40, 'n_episodes': 3,
                   'r2': 0.5, 'partial_r2': 0.4, 'impact_max': 1.0, 'reasons': []}}
    monkeypatch.setattr(SP, 'calibration', lambda: (cal, ('kernel.calibration@t', 'h')))
    r = server_client.post('/api/hot/scenario_pnl', json={'shocks': [{'id': 'TSMC', 'magnitude': 1}], 'record': False,
                                                          'positions': [{'id': 'Nvidia', 'usd': 1800},
                                                                        {'id': 'Apple', 'usd': 1004}]}).get_json()
    p = r['data']['pnl']
    assert p['status'] == 'ok'
    pnl, band = round(abs(p['pnl_usd'])), round(p['band_usd'])
    out = _run(server_client, 'en', 1440)
    want = f'Your portfolio: −{pnl:,} ± {band:,} USD (estimate from 3 episodes)'
    for k in ('xray', 'cabina', 'livesim'):
        assert out[k]['text'].startswith(want), (k, out[k]['text'], want)


def test_sin_posiciones_no_hay_linea(server_client):
    out = _run(server_client, 'es', 1440, pos={})
    for k in ('xray', 'cabina'):
        assert out[k] is None or not out[k]['shown'], (k, out[k])
    assert not [s for s in out['seen'] if s[1] == '/api/hot/scenario_pnl']
