"""tests/test_maptime_asof.py — DT-M3 (batch I3): el ⏱ del mapa usa el viaje en el tiempo del SERVIDOR.

  · con base: lo vigente en la fecha lo dice /api/ontology/graph?as_of= (+ known_at = G(t, κ)); el mapa apaga
    EXACTAMENTE lo que el servidor no trae, y la barra dice la fuente;
  · sin base (503) o sin conexión: UNA regla de respaldo rotulada, la MISMA con la que la migración carga el
    catálogo (vínculo sin fecha = "desde que se rastrea", 2000-01-01; hechos con fecha en su ventana) — ya no la
    fundación ni la fecha del par;
  · paridad (con DATABASE_URL): para cada vínculo del catálogo y varias fechas, la regla de respaldo del navegador
    da lo mismo que as_of_graph del servidor sobre la base migrada del mismo snapshot.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
NODE = shutil.which('node')
DATABASE_URL = os.getenv('DATABASE_URL', '')
DATES = ('1995-06-01', '2010-01-01', '2018-01-01', '2020-01-01', '2024-06-01')

HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const ROOT = process.argv[2], MODE = process.argv[3], DATES = JSON.parse(process.argv[4]);
const SRV = process.argv[5] ? JSON.parse(fs.readFileSync(process.argv[5], 'utf8')) : null;
const g = JSON.parse(fs.readFileSync(ROOT + '/data/grafo_v0.json', 'utf8'));
const urls = [];
const NODE_BY_ID = {}; g.nodes.forEach(n => { NODE_BY_ID[n.id] = n; });
const el = () => null;
const win = {
  LANG: 'es', NODE_BY_ID, NODE_META: {}, LINKS: g.links.map(l => ({ source: l.source, target: l.target, type: l.type })),
  TEMPORAL_SEED_FACTS: g.temporal_facts, ONTOLOGY: { objects: [] }, refreshStyles() {},
  localStorage: { getItem() { return null; } },
};
const sandbox = {
  window: win, console, setTimeout, clearTimeout, setInterval, clearInterval, Date, JSON, Set, Map, Object, Math,
  requestAnimationFrame: fn => setTimeout(fn, 0),
  localStorage: win.localStorage,
  document: { readyState: 'complete', querySelector: el, getElementById: el, addEventListener() {},
              createElement() { return { style: {} }; }, head: { appendChild() {} } },
  fetch(url) {
    urls.push(url);
    if (MODE === 'offline') return Promise.reject(new Error('offline'));
    if (MODE === 'nodb') return Promise.resolve({ status: 503, ok: false, json: () => Promise.resolve({ error: 'sin base' }) });
    const day = decodeURIComponent(url.split('as_of=')[1].split('&')[0]);
    return Promise.resolve({ status: 200, ok: true, json: () => Promise.resolve(SRV[day]) });
  },
};
sandbox.window.fetch = sandbox.fetch;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(ROOT + '/engine/maptime.js', 'utf8'), sandbox);
const MT = win.KhipuMapTime;
const wait = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const out = { urls, dates: {} };
  for (const d of DATES) {
    MT.setDate(d, d === '2020-01-01' && MODE === 'db' ? { known_at: '2026-01-01' } : { known_at: null });
    await wait(330);
    const on = [];
    win.LINKS.forEach((l, i) => { if (MT.linkOk(l)) on.push(i); });
    const nodes = Object.keys(NODE_BY_ID).filter(id => MT.nodeOk(id)).length;
    out.dates[d] = { links_on: on, nodes_on: nodes, source: MT.source };
  }
  MT.close();
  out.after_close = win.LINKS.every(l => MT.linkOk(l));
  console.log(JSON.stringify(out));
})();
"""


def _run(tmp_path, mode, srv=None):
    if not NODE:
        pytest.skip('node no disponible')
    h = tmp_path / 'h.js'
    h.write_text(HARNESS, encoding='utf-8')
    args = [NODE, str(h), ROOT, mode, json.dumps(list(DATES))]
    if srv is not None:
        p = tmp_path / 'srv.json'
        p.write_text(json.dumps(srv), encoding='utf-8')
        args.append(str(p))
    r = subprocess.run(args, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def _snap():
    with open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8') as fh:
        return json.load(fh)


def test_sin_base_regla_unica_del_catalogo(tmp_path):
    g = _snap()
    out = _run(tmp_path, 'nodb')
    n = len(g['links'])
    assert out['dates']['2018-01-01']['links_on'] == list(range(n))           # ≥ 2000: todo el catálogo
    assert out['dates']['2024-06-01']['source'] == 'catalog'
    old = out['dates']['1995-06-01']['links_on']
    assert len(old) < 20                                                     # antes de 2000: solo hechos con fecha
    # la regla es la del servidor: en 1995 solo los pares con un hecho fechado vigente en 1995
    on95 = set()
    for f in g['temporal_facts']:
        if f.get('object_type') == 'node' and f['valid_from'] <= '1995-06-01' and \
                (not f.get('valid_until') or '1995-06-01' < f['valid_until']):
            on95.add(frozenset((f['subject'], f['object'])))
    exp = [i for i, l in enumerate(g['links']) if frozenset((l['source'], l['target'])) in on95]
    assert old == exp
    assert out['after_close'] is True
    # pidió al servidor UNA vez: el 503 la deja en la regla de respaldo (no insiste en cada movimiento)
    assert len(out['urls']) == 1 and '/api/ontology/graph?as_of=' in out['urls'][0]


def test_con_base_sigue_al_servidor_y_pasa_known_at(tmp_path):
    g = _snap()
    links = g['links']
    # servidor falso: en cada fecha trae un subconjunto distinto (lo que diga el servidor manda)
    srv = {}
    for k, d in enumerate(DATES):
        keep = [l for i, l in enumerate(links) if i % (k + 2) == 0]
        srv[d] = {'as_of': d, 'links': [{'source': l['source'], 'target': l['target'], 'rel_type': l['type']}
                                        for l in keep], 'nodes': [], 'counts': {'links': len(keep)}}
    out = _run(tmp_path, 'db', srv)
    for k, d in enumerate(DATES):
        want_pairs = {(l['source'], l['target']) for i, l in enumerate(links) if i % (k + 2) == 0}
        exp = [i for i, l in enumerate(links) if (l['source'], l['target']) in want_pairs
               or (l['target'], l['source']) in want_pairs]
        assert out['dates'][d]['links_on'] == exp, d
        assert out['dates'][d]['source'] == 'db'
    assert any('known_at=2026-01-01' in u and 'as_of=2020-01-01' in u for u in out['urls'])
    assert not any('known_at' in u for u in out['urls'] if 'as_of=2018-01-01' in u)


def test_sin_conexion_cae_a_la_regla_rotulada(tmp_path):
    out = _run(tmp_path, 'offline')
    assert out['dates']['2018-01-01']['source'] == 'catalog'
    assert len(out['dates']['2018-01-01']['links_on']) == len(_snap()['links'])


def test_maptime_ya_no_usa_fundacion_ni_fecha_del_par():
    src = open(os.path.join(ROOT, 'engine', 'maptime.js'), encoding='utf-8').read()
    assert 'founded' not in src and 'pairFrom' not in src
    assert '/api/ontology/graph?as_of=' in src and 'known_at' in src
    assert "Fuente: base de datos" in src and 'Source: database' in src and 'Fuente: regla del catálogo' in src


# ── paridad con el servidor (Postgres) ───────────────────────────────────────
@pytest.fixture(scope='module')
def migrated():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL (Postgres)')
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()
    script = os.path.join(ROOT, 'scripts', 'migrate_v0_to_ontology.py')
    r = subprocess.run([sys.executable, script, '--reset'], capture_output=True, text=True,
                       env={**os.environ, 'DATABASE_URL': DATABASE_URL, 'PYTHONIOENCODING': 'utf-8'})
    assert r.returncode == 0, r.stderr
    yield
    Base.metadata.drop_all(engine)


def test_paridad_regla_de_respaldo_vs_servidor(migrated, tmp_path):
    from ontology.db import session_scope
    from ontology.service import as_of_graph
    g = _snap()
    out = _run(tmp_path, 'nodb')
    with session_scope() as s:
        for d in DATES:
            gr = as_of_graph(s, d)
            pairs = {(l['source'], l['target']) for l in gr['links']}
            srv_on = [i for i, l in enumerate(g['links'])
                      if (l['source'], l['target']) in pairs or (l['target'], l['source']) in pairs]
            assert out['dates'][d]['links_on'] == srv_on, (d, len(out['dates'][d]['links_on']), len(srv_on))


# ── revisión lote I: sin tormenta de reintentos, ▶ que anima con la base, 503 pasajero ──────────────────────────
HARNESS2 = r"""
const fs = require('fs'), vm = require('vm');
const ROOT = process.argv[2], MODE = process.argv[3];
const urls = [];
const NODE_BY_ID = { a: { id: 'a' }, b: { id: 'b' } };
const win = { LANG: 'es', NODE_BY_ID, NODE_META: {}, LINKS: [{ source: 'a', target: 'b', type: 'supply' }],
              TEMPORAL_SEED_FACTS: [], ONTOLOGY: { objects: [] }, refreshStyles() {},
              localStorage: { getItem() { return null; } } };
let state = 'up';
const sandbox = {
  window: win, console, setTimeout, clearTimeout, setInterval, clearInterval, Date, JSON, Set, Map, Object, Math,
  requestAnimationFrame: fn => setTimeout(fn, 0), localStorage: win.localStorage,
  document: { readyState: 'complete', querySelector: () => null, getElementById: () => null, addEventListener() {},
              createElement() { return { style: {} }; }, head: { appendChild() {} } },
  fetch(url) {
    urls.push(url);
    if (MODE === 'bad') return Promise.resolve({ status: 400, ok: false, json: () => Promise.resolve({ error: 'known_at inválido' }) });
    if (MODE === 'reject') return Promise.reject(new TypeError('Failed to fetch'));
    if (MODE === 'sw' && state === 'off') return Promise.resolve({ status: 503, ok: false, json: () => Promise.resolve({ offline: true }) });
    if (MODE === 'blip' && state === 'off') return Promise.resolve({ status: 503, ok: false, json: () => Promise.resolve({ error: 'sin base' }) });
    const day = decodeURIComponent(url.split('as_of=')[1].split('&')[0]);
    const body = { as_of: day, links: day < '2010' ? [] : [{ source: 'a', target: 'b' }], nodes: [] };
    return new Promise(r => setTimeout(() => r({ status: 200, ok: true, json: () => Promise.resolve(body) }), 40));
  },
};
sandbox.window.fetch = sandbox.fetch;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(ROOT + '/engine/maptime.js', 'utf8'), sandbox);
const MT = win.KhipuMapTime;
const wait = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const out = { mode: MODE };
  if (MODE === 'bad' || MODE === 'reject') {
    MT.setDate('2024-01-01', { known_at: 'xyz' });
    await wait(3000);
    out.fetches = urls.length; out.source = MT.source;
  } else if (MODE === 'play') {
    MT.setDate('2026-10-01');
    await wait(400);
    out.before = MT.linkOk(win.LINKS[0]);
    MT.setDate(Date.now() + 1e10);                     // al final del deslizador: ▶ arranca en 1995
    const n0 = urls.length;
    MT.togglePlay();                                   // desde hoy → salta a 1995 y avanza cada 160 ms
    await wait(1200);
    out.playing = MT.playing; out.during = urls.length - n0;
    out.year = new Date(MT.dateMs).getUTCFullYear(); out.linkOk_early = MT.linkOk(win.LINKS[0]); out.source = MT.source;
    MT.togglePlay();
  } else {                                             // 'sw' (503 offline del service worker) | 'blip' (503 de la base)
    state = 'off';
    MT.setDate('2024-01-01');
    await wait(400);
    out.offSource = MT.source;
    state = 'up';
    MT.close(); MT.open(); MT.setDate('2024-02-01');
    await wait(400);
    out.backSource = MT.source; out.fetches = urls.length;
  }
  console.log(JSON.stringify(out));
  process.exit(0);
})();
"""


def _run2(tmp_path, mode):
    if not NODE:
        pytest.skip('node no disponible')
    h = tmp_path / 'h2.js'
    h.write_text(HARNESS2, encoding='utf-8')
    r = subprocess.run([NODE, str(h), ROOT, mode], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize('mode', ['bad', 'reject'])
def test_una_foto_que_falla_no_se_pide_4_veces_por_segundo(tmp_path, mode):
    """Antes: 400 (known_at inválido) o red caída → ~11 pedidos en 3 s, sin fin, al endpoint pesado."""
    out = _run2(tmp_path, mode)
    assert out['fetches'] <= 2, out
    assert out['source'] == 'catalog'


def test_play_con_base_anima_con_las_fotos_del_servidor(tmp_path):
    """Antes: la espera de 250 ms nunca vencía (pasos de 160 ms) → 0 pedidos y la foto de HOY en 1995."""
    out = _run2(tmp_path, 'play')
    assert out['before'] is True and out['playing'] is True
    assert out['during'] >= 2 and out['year'] < 2010 and out['linkOk_early'] is False and out['source'] == 'db'


@pytest.mark.parametrize('mode', ['sw', 'blip'])
def test_un_503_pasajero_no_deja_sin_base_para_siempre(tmp_path, mode):
    out = _run2(tmp_path, mode)
    assert out['offSource'] == 'catalog'
    assert out['backSource'] == 'db', out                 # al volver a abrir ⏱ se pide de nuevo
