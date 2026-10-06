"""Khipus OS · velocidad al arrancar (2026-10-06).

1. El mapa d3 NO se calcula mientras Khipus OS lo tapa: resize() solo pide; _ensureMapSettled()
   asienta (por porciones la primera vez) cuando el mapa se ve, y no hace nada si el tamaño no cambió.
2. El brief matinal no se abre solo encima de Khipus OS (queda a pedido) y no recorre las 949
   empresas si el motor de matrices ya trae el chokepoint.
3. /api/matrix/insights: dos pedidos iguales a la vez → UNA construcción y UNA narración de IA.
"""
import json
import os
import re
import shutil
import subprocess
import threading
import time
from contextlib import contextmanager

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
HTML = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
BRIEF = open(os.path.join(ROOT, 'engine', 'brief.js'), encoding='utf-8').read()


def _grab(rx):
    m = re.search(rx, HTML, re.S)
    assert m, rx
    return m.group(0)


# ════════════════════════════════════════════════════════════════════════════
# 1 · Mapa: guardas estáticas (contrato con CLAUDE.md "Mapa principal")
# ════════════════════════════════════════════════════════════════════════════

def test_la_simulacion_se_detiene_al_crearse_salvo_vista_clasica():
    i = HTML.index('const sim = d3.forceSimulation(NODES)')
    seg = HTML[i:i + 1600]
    assert "sessionStorage.getItem('kh_os_classic') === '1'" in seg and 'if(!_mapClassicBoot) sim.stop();' in seg
    assert 'let _mapOsExpected = !_mapClassicBoot;' in HTML


def test_resize_solo_pide_y_la_guarda_mira_si_khipus_os_tapa_el_mapa():
    assert 'function resize(){ _ensureMapSettled(false); }' in HTML
    cov = _grab(r'function _mapCovered\(\)\{.*?\n\}')
    assert 'document.hidden' in cov and '_mapBootWaiting()' in cov
    assert "getElementById('bcp-ov')" in cov and 'contains(svg.node())' in cov
    boot = _grab(r'function _mapBootWaiting\(\)\{.*?\n\}')
    assert "sessionStorage.getItem('kh_os_classic')" in HTML       # vista clásica = el mapa es la pantalla
    assert 'ck.isOpen()' in boot or '_mapCkOpen()' in boot
    assert 'window._ensureMapSettled = _ensureMapSettled;' in HTML


def test_capitalizacion_en_vivo_no_reasienta_un_mapa_tapado():
    fn = _grab(r'function _resizeNodesByCap\(\)\{.*?\n\}')
    assert 'settleGraph(' not in fn                     # antes: settleGraph(.12, 60) a ciegas cada 15 min
    assert '_mapReheat = true;' in fn and '_ensureMapSettled(false)' in fn


def test_camara_espera_posiciones_reales():
    fit = _grab(r'function fitToView\(dur=500\)\{.*?\n\}')
    fly = _grab(r'function flyToNode\(d,yFrac=0\.5,dur=650\)\{.*?\n\}')
    for f in (fit, fly):
        assert '_ensureMapSettled(false)' in f and '_mapLaidOnce' in f
    assert '_mapFitPending = true' in fit and '_mapFlyPending = {' in fly


def test_senales_de_visibilidad_y_sin_relayout_vivo_fuera_del_arrastre():
    assert 'new ResizeObserver(' in HTML and "addEventListener('visibilitychange'" in HTML
    assert "addEventListener('pointerenter'" in HTML
    # la física solo se pinta en vivo durante el arrastre (regla "Mapa principal")
    region = HTML[HTML.index('const sim = d3.forceSimulation(NODES)'):HTML.index('window.settleGraph = settleGraph;')]
    assert region.count('.restart()') == 1 and "on('start'" in region


# ════════════════════════════════════════════════════════════════════════════
# 1b · Mapa: comportamiento real (el código se extrae de app.html y corre en node)
# ════════════════════════════════════════════════════════════════════════════

_PRELUDE = r'''
const store = Object.assign({}, __SS__), lstore = Object.assign({}, __LS__);
global.window = { LANG: 'es' };
global.sessionStorage = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
global.localStorage = { getItem: k => (k in lstore ? lstore[k] : null), setItem: (k, v) => { lstore[k] = String(v); } };
let viewMode = 'flow';
let rect = { width: 1000, height: 600 };
let ovContains = false, docHidden = false, bootEl = null;
const ov = { contains: () => ovContains };
global.document = { get hidden() { return docHidden; }, getElementById: id => (id === 'bcp-ov' ? ov : id === 'boot' ? bootEl : null) };
const svgNode = { getBoundingClientRect: () => rect };
const appended = [], cam = [];
const svg = {
  node: () => svgNode,
  append: () => { const t = { attrs: {}, attr(k, v) { this.attrs[k] = v; return this; }, style() { return this; },
                               text(s) { this.txt = s; return this; }, remove() { this.removed = true; } };
                  appended.push(t); return t; },
  transition: () => ({ duration() { return this; }, ease() { return this; }, call() { cam.push('move'); return this; } }),
};
const rootStyle = {};
const root = { style(k, v) { if (arguments.length === 1) return rootStyle[k]; if (v === null) delete rootStyle[k]; else rootStyle[k] = v; return this; } };
let ticks = 0, alpha = 0, paints = 0, forces = 0, tickMs = 1;
const sim = { stop() { return this; }, alpha(a) { if (a === undefined) return alpha; alpha = a; return this; },
              alphaMin() { return 0.001; }, tick() { ticks++; alpha *= 0.96; const t = Date.now(); while (Date.now() - t < tickMs) {} } };
function _paintGraph() { paints++; }
function setForces() { forces++; }
function positionRegionLabels() {}
const d3 = { zoomTransform: () => ({ k: 1 }), zoomIdentity: { translate() { return { scale() { return 'T'; } }; } }, easeCubicInOut: null };
const zoom = { transform: 'zt' };
const NODES = [{ id: 'a', x: 1, y: 2 }, { id: 'b', x: 3, y: 4 }];
const NODE_BY_ID = { a: NODES[0], b: NODES[1] };
let W = 0, H = 0, _liveTick = false, selected = null;
const _mapClassicBoot = store.kh_os_classic === '1';     // en app.html se calcula al crear la simulación
const wait = ms => new Promise(r => setTimeout(r, ms));
async function settled() { for (let i = 0; i < 400 && !_mapLaidOnce; i++) await wait(5); }
'''


def _map_js(scenario, session=None, local=None):
    src = '\n'.join([
        _grab(r'let _mapLaidOnce = false;.*?function resize\(\)\{ _ensureMapSettled\(false\); \}'),
        _grab(r'function settleGraph\(alpha=\.4, maxTicks=200\)\{.*?\n\}'),
        _grab(r'function fitToView\(dur=500\)\{.*?\n\}'),
        _grab(r'function flyToNode\(d,yFrac=0\.5,dur=650\)\{.*?\n\}'),
    ])
    js = (_PRELUDE.replace('__SS__', json.dumps(session or {})).replace('__LS__', json.dumps(local or {})) + src +
          '\n(async () => { const out = {};\n' + scenario + '\nprocess.stdout.write(JSON.stringify(out), () => process.exit(0)); })()'
          '.catch(e => { console.error(e && e.stack || e); process.exit(1); });')
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_mapa_tapado_por_khipus_os_no_se_calcula_y_se_asienta_al_mostrarse():
    o = _map_js(r'''
      window.BixbyCockpit = { isOpen: () => true, open() {} };
      resize(); resize(); await wait(30);
      out.covered = { ticks, laid: _mapLaidOnce, hidden: root.style('visibility') === 'hidden', state: window._mapState() };
      // jumpTo mientras está tapado → el vuelo queda pendiente (no cámara sobre posiciones falsas)
      selected = 'b'; flyToNode(NODE_BY_ID.b, 0.5, 650); fitToView();
      out.pendingCam = cam.length;
      // la ventana "Grafo" adopta el mapa dentro de Khipus OS → se ve → primer asentado por porciones
      ovContains = true; resize();
      out.started = { settling: window._mapState().settling, laid: _mapLaidOnce, hint: (appended[0] || {}).txt };
      await settled();
      out.done = { ticks, laid: _mapLaidOnce, hidden: root.style('visibility') === 'hidden', paints,
                   hintRemoved: !!(appended[0] && appended[0].removed), cam: cam.length };
      // mismo tamaño → cero trabajo
      const t0 = ticks; resize(); resize(); out.sameSizeTicks = ticks - t0;
      // tamaño nuevo → reasentado LIGERO síncrono (≤ 60 ticks)
      rect = { width: 900, height: 500 }; const t1 = ticks; resize(); out.resizedTicks = ticks - t1; out.WH = [W, H];
      // capitalización en vivo con el mapa tapado → espera; al mostrarse, separa solapes
      ovContains = false; _mapReheat = true; const t2 = ticks; out.reheatCovered = _ensureMapSettled(false); out.reheatCoveredTicks = ticks - t2;
      ovContains = true; resize(); out.reheatTicks = ticks - t2; out.reheatLeft = _mapReheat;
    ''')
    assert o['covered']['ticks'] == 0 and not o['covered']['laid'] and o['covered']['hidden']
    assert o['covered']['state']['covered'] is True
    assert o['pendingCam'] == 0
    assert o['started']['settling'] and not o['started']['laid']
    assert o['started']['hint'] == 'Ordenando el mapa de 2 empresas…'
    d = o['done']
    assert d['laid'] and not d['hidden'] and d['paints'] == 1 and d['hintRemoved']
    assert 0 < d['ticks'] <= 80
    assert d['cam'] == 1                               # el vuelo pendiente a 'b' se hizo al terminar
    assert o['sameSizeTicks'] == 0
    assert 0 < o['resizedTicks'] <= 60 and o['WH'] == [900, 500]
    assert o['reheatCovered'] is False and o['reheatCoveredTicks'] == 0
    assert 0 < o['reheatTicks'] <= 60 and o['reheatLeft'] is False


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_arranque_hacia_el_os_espera_y_vista_clasica_asienta_enseguida():
    # arranque normal: Khipus OS todavía no cargó → el mapa cuenta como tapado
    o = _map_js(r'''
      resize(); await wait(20);
      out.ticks = ticks; out.state = window._mapState();
    ''')
    assert o['ticks'] == 0 and o['state']['bootWaiting'] is True and o['state']['laid'] is False
    # "Vista clásica" en esta sesión → el mapa ES la pantalla: se asienta sin esperar al OS
    o = _map_js(r'''
      resize(); await settled();
      out.ticks = ticks; out.state = window._mapState();
    ''', session={'kh_os_classic': '1'})
    assert o['ticks'] > 0 and o['state']['laid'] is True and o['state']['osExpected'] is False
    # vista clásica con el splash de arranque todavía encima → de una vez (aparece listo al desvanecerse)
    o = _map_js(r'''
      bootEl = { classList: { contains: () => false } };
      resize();
      out.ticks = ticks; out.laid = _mapLaidOnce; out.settling = window._mapState().settling;
    ''', session={'kh_os_classic': '1'})
    assert 0 < o['ticks'] <= 60 and o['laid'] is True and o['settling'] is False   # la receta de siempre (.15, 60)
    # la Cabina cargó, el arranque terminó (#boot fuera) y no se abrió → se rinde y asienta
    o = _map_js(r'''
      window.BixbyCockpit = { isOpen: () => false, open() {} };
      resize(); out.first = ticks;            // recién vista: aún espera
      await wait(650); resize(); await settled();
      out.ticks = ticks; out.laid = _mapLaidOnce;
    ''')
    assert o['first'] == 0 and o['ticks'] > 0 and o['laid'] is True


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_memoria_del_mapa_acelera_la_siguiente_apertura():
    # 1.ª vez: orden desde cero (≤ 80 ticks) y se guarda la disposición (x relativa al ancho, y al centro)
    o = _map_js(r'''
      window.BixbyCockpit = { isOpen: () => true, open() {} };
      ovContains = true; NODES[0].x = 0; NODES[0].y = 0;
      resize(); await settled(); await wait(20); out.savedEarly = !!lstore.kh_map_pos_v1; await wait(1300);   // se guarda al asentar y otra vez ya quieto (1,2 s)
      out.ticks = ticks; out.seeded = window._mapState().seeded; out.saved = lstore.kh_map_pos_v1 || null;
    ''')
    assert 0 < o["ticks"] <= 80 and o["seeded"] is False and o["saved"] and o["savedEarly"] is True
    saved = json.loads(o['saved'])
    assert saved['v'] == 1 and saved['W'] == 1000 and set(saved['p']) == {'a', 'b'}
    assert saved['p']['b'] == [round(3 / 1000, 4), 4 - 300]          # x/W, y − H/2
    # 2.ª vez (otro arranque, ventana un poco más ancha): parte de la memoria con un asentado corto
    o = _map_js(r'''
      window.BixbyCockpit = { isOpen: () => true, open() {} };
      ovContains = true; rect = { width: 1100, height: 700 };
      resize(); await settled();
      out.ticks = ticks; out.seeded = window._mapState().seeded; out.b = [NODES[1].x, NODES[1].y];
    ''', local={'kh_map_pos_v1': o['saved']})
    assert o['seeded'] is True and 0 < o['ticks'] <= 30
    assert abs(o['b'][0] - 0.003 * 1100) < 1e-6 and abs(o['b'][1] - (4 - 300 + 350)) < 1e-6
    # otra empresa en el catálogo → firma distinta → orden desde cero (nunca una disposición ajena)
    bad = dict(saved, sig='3:123')
    o = _map_js(r'''
      window.BixbyCockpit = { isOpen: () => true, open() {} };
      ovContains = true; resize(); await settled();
      out.seeded = window._mapState().seeded; out.ticks = ticks;
    ''', local={'kh_map_pos_v1': json.dumps(bad)})
    assert o['seeded'] is False and o['ticks'] > 30


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_porciones_se_pausan_si_el_mapa_se_vuelve_a_tapar():
    o = _map_js(r'''
      window.BixbyCockpit = { isOpen: () => true, open() {} };
      tickMs = 6; ovContains = true; resize();   // ~16 ticks por porción de 80 ms → varias porciones
      await wait(0); ovContains = false;                  // la ventana se cerró a mitad de camino
      await wait(60);
      out.paused = window._mapState().paused; out.laid = _mapLaidOnce; const t = ticks;
      await wait(60); out.idleTicks = ticks - t;
      ovContains = true; resize(); await settled();
      out.laidAfter = _mapLaidOnce;
    ''')
    assert o['paused'] is True and o['laid'] is False and o['idleTicks'] == 0 and o['laidAfter'] is True


# ════════════════════════════════════════════════════════════════════════════
# 2 · Brief matinal
# ════════════════════════════════════════════════════════════════════════════

_BRIEF_PRELUDE = r'''
const store = Object.assign({}, __SS__), lstore = {};
const els = {}, fetched = [];
let downstreamCalls = 0;
function mk(id) {
  return els[id] || (els[id] = { id, innerHTML: '', textContent: '', title: '', className: '', style: {},
    classList: { s: new Set(), add(c) { this.s.add(c); }, remove(c) { this.s.delete(c); }, contains(c) { return this.s.has(c); } },
    addEventListener() {}, appendChild() {} });
}
global.sessionStorage = { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
global.localStorage = { getItem: k => (k in lstore ? lstore[k] : null), setItem: (k, v) => { lstore[k] = String(v); } };
global.document = {
  readyState: 'complete',
  querySelector: s => (s === '.graph-wrap' ? {} : null),
  getElementById: id => (id === 'brief-fab' || id === 'brief-ov' ? (els[id] || null) : mk(id)),
  createElement: () => ({ id: '', innerHTML: '', style: {}, addEventListener() {},
    classList: { s: new Set(), add(c) { this.s.add(c); }, remove(c) { this.s.delete(c); }, contains(c) { return this.s.has(c); } } }),
  body: { appendChild(e) { if (e.id) els[e.id] = e; } },
  head: { appendChild(e) { if (e.id) els[e.id] = e; } },
};
global.window = global;
window.LANG = 'es';
window.addEventListener = () => {};
window.NODES = [{ id: 'a', label: 'A' }, { id: 'b', label: 'B' }, { id: 'c', label: 'C' }];
window.NODE_BY_ID = { a: window.NODES[0], b: window.NODES[1], c: window.NODES[2] };
window.computeDownstream = id => { downstreamCalls++; return new Set(id === 'b' ? ['x', 'y'] : ['x']); };
window.computeNRS = () => 40;
const realSetTimeout = setTimeout;
global.setTimeout = (f, ms) => realSetTimeout(f, ms > 100 ? 5 : ms);   // el arranque del brief espera 1,4 s
global.fetch = (u) => { fetched.push(String(u)); return Promise.resolve(__FETCH__(String(u))); };
const wait = ms => new Promise(r => realSetTimeout(r, ms));
'''


def _brief_js(scenario, session=None, fetch_js='u => ({ ok: false })'):
    js = (_BRIEF_PRELUDE.replace('__SS__', json.dumps(session or {})).replace('__FETCH__', '(' + fetch_js + ')') +
          '\n' + scenario.split('/*LOAD*/')[0] + '\n' + BRIEF + '\n(async () => { const out = {};\n' +
          scenario.split('/*LOAD*/')[1] + '\nprocess.stdout.write(JSON.stringify(out), () => process.exit(0)); })()'
          '.catch(e => { console.error(e && e.stack || e); process.exit(1); });')
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_brief_no_se_abre_solo_sobre_khipus_os_pero_si_a_pedido():
    o = _brief_js(r'''
      window.BixbyCockpit = { isOpen: () => false, open() {} };   // existe → el OS se abrirá al arrancar
      /*LOAD*/
      await wait(80);
      out.auto = !!(els['brief-ov'] && els['brief-ov'].classList.contains('show'));
      out.fetchedAtBoot = fetched.slice(); out.downstreamAtBoot = downstreamCalls;
      window._briefOpen(); await wait(80);
      out.onDemand = !!(els['brief-ov'] && els['brief-ov'].classList.contains('show'));
      out.src = els['brief-src'] && els['brief-src'].textContent;
      out.cards = els['brief-cards'] && els['brief-cards'].innerHTML;
      out.downstream = downstreamCalls; out.allowed = window._briefAutoAllowed();
    ''')
    assert o['auto'] is False and o['fetchedAtBoot'] == [] and o['downstreamAtBoot'] == 0
    assert o['allowed'] is False
    assert o['onDemand'] is True
    assert o['downstream'] == 3                                    # sin motor de matrices → cálculo local
    assert 'El mayor punto único de fallo hoy es <b>B</b>' in o['cards']
    assert o['src'].startswith('Fuente: grafo de Khipus, calculado en tu navegador')


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_brief_vista_clasica_se_abre_y_usa_la_matriz_sin_recorrer_las_empresas():
    o = _brief_js(r'''
      window.BixbyCockpit = { isOpen: () => false, open() {} };
      window.LANG = 'en';
      /*LOAD*/
      await wait(120);
      out.auto = !!(els['brief-ov'] && els['brief-ov'].classList.contains('show'));
      out.downstream = downstreamCalls; out.fetched = fetched.slice();
      out.cards = els['brief-cards'] && els['brief-cards'].innerHTML; out.src = els['brief-src'] && els['brief-src'].textContent;
    ''', session={'kh_os_classic': '1'},
        fetch_js="u => (u.indexOf('/api/matrix/metrics') === 0 ? { ok: true, json: () => Promise.resolve("
                 "{ chokepoints_top25: [{ id: 'c', cascade_size: 7 }], factors_active: [] }) } : { ok: false })")
    assert o['auto'] is True
    assert o['downstream'] == 0                                    # el servidor ya trajo el chokepoint
    assert '/api/matrix/metrics' in o['fetched'] and any(u.startswith('/api/committee/board') for u in o['fetched'])
    assert 'Network chokepoint (matrix engine): <b>C</b>' in o['cards'] and 'drags down <b>7</b> companies' in o['cards']
    assert o['src'].startswith('Source: Khipus matrix engine (ontology)')


def test_brief_textos_bilingues_y_sobre_el_os():
    assert "z-index:7600" in BRIEF                    # por encima de Khipus OS (7000), debajo del Comité (7650)
    for es, en in (("'RIESGO'", "'RISK'"), ("'FACTOR ACTIVO'", "'ACTIVE FACTOR'"), ("'OPORTUNIDAD'", "'OPPORTUNITY'"),
                   ("'Vigílala.'", "'Keep an eye on it.'"), ("'Brief matinal'", "'Morning brief'")):
        assert es in BRIEF and en in BRIEF, (es, en)


# ════════════════════════════════════════════════════════════════════════════
# 3 · /api/matrix/insights: un cálculo por clave aunque lleguen dos a la vez
# ════════════════════════════════════════════════════════════════════════════

class _FakeSession:
    def execute(self, *a, **k):
        class _R:
            def all(self):
                return []
        return _R()


@contextmanager
def _fake_scope():
    yield _FakeSession()


@pytest.fixture
def insights_env(monkeypatch):
    import numpy as np

    import matrix.api as M
    import matrix.engine as E
    from core import http as h
    with h._rate_lock:
        h._rate_buckets.clear()
    monkeypatch.setattr(M, '_TTL_CACHE', {})
    monkeypatch.setattr(M, '_INFLIGHT', {})
    monkeypatch.setattr(M, '_db', lambda: _fake_scope)
    monkeypatch.setattr(E, '_graph_epoch', lambda s: 'EPOCH-TEST')
    calls = {'build': 0, 'narrate': 0, 'persist': 0}

    def build_matrices(s, as_of=None):
        calls['build'] += 1
        if calls.get('fail_first') and calls['build'] == 1:
            time.sleep(0.3)
            raise RuntimeError('fallo simulado')
        ids = ['A', 'B', 'C']
        return {'supply': np.array([[0, 1, 0], [0, 0, 1], [0, 0, 0]], float)}, {k: i for i, k in enumerate(ids)}, ids

    def narrate(situation, lang, tier):
        calls['narrate'] += 1
        time.sleep(0.6)                                   # una narración de IA tarda
        return [{'title': 't', 'detail': 'd', 'kind': 'estructura'}], 'fake:' + tier

    monkeypatch.setattr(E, 'build_matrices', build_matrices)
    monkeypatch.setattr(E, 'active_factors', lambda s, as_of=None: [])
    monkeypatch.setattr(E, 'fragility', lambda idx, factors: None)
    monkeypatch.setattr(E, 'propagate', lambda mats, idx, ids, shock, magnitude=1.0, frag=None:
                        ({'B': 1.0, 'C': 0.5}, [{'id': 'C', 'impact': 0.5, 'hop': 1}]))
    monkeypatch.setattr(M, '_narrate_insights', narrate)
    monkeypatch.setattr(M, '_persist_insight', lambda *a, **k: calls.__setitem__('persist', calls['persist'] + 1))
    from flask import Flask
    app = Flask('khipus_os_perf_test')
    app.config['TESTING'] = True
    app.register_blueprint(M.matrix_bp)
    yield app, calls, M
    with h._rate_lock:
        h._rate_buckets.clear()


def _post_concurrently(app, bodies, gap=0.1):
    out = [None] * len(bodies)

    def run(i, body):
        try:
            r = app.test_client().post('/api/matrix/insights', json=body)
            out[i] = (r.status_code, r.get_json())
        except Exception as e:  # noqa: BLE001 — TESTING propaga la excepción del primero
            out[i] = ('error', str(e))

    ths = []
    for i, b in enumerate(bodies):
        t = threading.Thread(target=run, args=(i, b))
        t.start()
        ths.append(t)
        time.sleep(gap)
    for t in ths:
        t.join(timeout=20)
        assert not t.is_alive(), 'un pedido quedó colgado esperando al otro'
    return out


def test_insights_dos_pedidos_iguales_a_la_vez_narran_una_sola_vez(insights_env):
    app, calls, M = insights_env
    a, b = _post_concurrently(app, [{'lang': 'es'}, {'lang': 'es'}])
    assert a[0] == 200 and b[0] == 200
    assert calls['build'] == 1 and calls['narrate'] == 1 and calls['persist'] == 1
    assert a[1]['insights'] == b[1]['insights'] and a[1]['model'] == b[1]['model'] == 'fake:fast'
    assert b[1].get('shared') is True and b[1].get('cached') is True
    assert M._INFLIGHT == {}
    # el tercero sale de la caché, sin construir ni narrar
    c = app.test_client().post('/api/matrix/insights', json={'lang': 'es'}).get_json()
    assert c['cached'] is True and calls['narrate'] == 1


def test_insights_claves_distintas_no_se_esperan(insights_env):
    app, calls, _M = insights_env
    a, b = _post_concurrently(app, [{'lang': 'es'}, {'lang': 'en'}])
    assert a[0] == 200 and b[0] == 200 and calls['narrate'] == 2 and not b[1].get('shared')


def test_insights_si_el_primero_falla_el_segundo_calcula_solo(insights_env):
    app, calls, M = insights_env
    calls['fail_first'] = True
    a, b = _post_concurrently(app, [{'lang': 'es'}, {'lang': 'es'}])
    assert a[0] in ('error', 500)
    assert b[0] == 200 and not b[1].get('shared') and calls['narrate'] == 1
    assert M._INFLIGHT == {}


def test_insights_shock_manual_no_se_comparte(insights_env):
    app, calls, M = insights_env
    a, b = _post_concurrently(app, [{'lang': 'es', 'shock': ['A']}, {'lang': 'es', 'shock': ['A']}])
    assert a[0] == 200 and b[0] == 200 and calls['narrate'] == 2
    assert not a[1].get('shared') and not b[1].get('shared') and calls['persist'] == 0
    assert M._INFLIGHT == {}
