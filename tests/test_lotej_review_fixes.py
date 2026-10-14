"""tests/test_lotej_review_fixes.py — arreglos de la revisión del LOTE J (servidor a 5.000 + chat progresivo F3).

  · /api/hot/card: la etiqueta (ETag) lleva la versión de fundamentales que USÓ el cuerpo (la ficha calcula solo su NRS
    sin rehacer el vector: antes un 304 dejaba un NRS viejo en el cliente);
  · vistas derivadas: la generación que leen los LECTORES (la privada del snapshot si la publicada no sirve) se guarda
    y no se suelta — antes cada ficha se rearmaba en cada pedido;
  · /api/hot/nrs: tope de 250 ids por GET (la línea del pedido de gunicorn) y engine/hotclient.js parte en 200;
  · progreso del chat: `seq` solo con bloques provisionales; los bloques solo para el navegador que preguntó;
  · 🩺 Gobernanza avisa si MATRIX_ENGINE=dense no se obedece; /api/matrix/parity no arma el denso a más de 2.000 nodos;
  · tensor: Ψᵀc exacta (math.fsum) y find_similar_entities con el mismo orden que tensor.peers;
  · genui: el 🩺 cuenta lo que cuestan los bloques provisionales.
"""
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
DATABASE_URL = os.getenv('DATABASE_URL', '')
NODE = shutil.which('node')


def _snapshot_gen(version=None):
    """Una generación del snapshot real publicada (sin base), como la arma el constructor."""
    from core.hotviews import registry, signals, source
    from core.hotviews.views import graph as graph_view
    from core.hotviews.views import graph_core, impact
    data = source.load_snapshot()
    if version is not None:
        data.graph_version = version
    core = graph_core.build(data)
    imp = impact.build(core)
    gv = graph_view.build(data)
    rel, label = signals.release_hash()
    g = registry.make(data, {'graph_core': core, 'impact': imp, 'graph': gv}, rel, label, {},
                      {'graph_core': core.content_sha, 'impact': imp.content_sha})
    gv.attach(g)
    return g


@pytest.fixture
def nodb(monkeypatch):
    import ontology.db as odb
    from core.hotviews import builder, derived, hot, registry
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    registry.reset()
    builder._ST.update(consecutive_failures=0, retry_at=0.0)
    hot.reset()
    derived.reset()
    yield
    registry.reset()
    hot.reset()
    derived.reset()


# ── /api/hot/card: la etiqueta sigue al NRS del cuerpo ─────────────────────────────────────────────────────────────
def test_card_etag_cambia_con_los_fundamentales_aunque_el_vector_no_se_rehaga(nodb, monkeypatch):
    from flask import Flask

    from core import live_fundamentals as lf
    from core.hotviews import registry
    from core.hotviews.api import hot_bp
    from core.hotviews.views import card
    g = _snapshot_gen()
    registry.publish(g)
    app = Flask(__name__)
    app.register_blueprint(hot_bp)
    c = app.test_client()
    monkeypatch.setitem(lf._STATE, 'runs', 1)
    monkeypatch.setitem(lf._STATE, 'data', {})
    card.view(g).nrs_all()                                   # el vector con la versión 1 (prewarm / world)
    r1 = c.get('/api/hot/card/Nvidia?structure=0')
    e1, n1 = r1.headers['ETag'], r1.get_json()['data']['nrs']
    monkeypatch.setitem(lf._STATE, 'runs', 2)               # tanda nueva: Nvidia con margen −50 %
    monkeypatch.setitem(lf._STATE, 'data', {'Nvidia': {'operating_margin': -50.0}})
    r2 = c.get('/api/hot/card/Nvidia?structure=0')
    e2, n2 = r2.headers['ETag'], r2.get_json()['data']['nrs']
    assert n1['fund_version'] == 1 and n2['fund_version'] == 2 and n1['value'] != n2['value']
    assert e1 != e2
    assert c.get('/api/hot/card/Nvidia?structure=0', headers={'If-None-Match': e1}).status_code == 200
    assert c.get('/api/hot/card/Nvidia?structure=0', headers={'If-None-Match': e2}).status_code == 304


# ── vistas derivadas: la generación de los lectores se guarda ────────────────────────────────────────────────────────
def test_la_generacion_de_los_lectores_no_se_rearma_en_cada_pedido(nodb):
    from core.hotviews import derived, hot
    from core.hotviews.views import card
    F = hot.fallback().generation_obj                         # sin publicada: los lectores leen la privada del snapshot
    card.view(F)
    for v in (1, 2):                                          # dos generaciones más nuevas, armadas y precalentadas
        card.view(_snapshot_gen(v))
    u0 = derived.stats()['uncached']
    for _ in range(4):
        card.view(F)
    assert derived.peek(F, 'card') is not None                # guardada…
    assert derived.stats()['uncached'] == u0                  # …y no se rearmó
    assert len(derived.stats()['generations']) <= derived._KEEP


# ── /api/hot/nrs: lote dentro de la línea del pedido ─────────────────────────────────────────────────────────────────
def test_nrs_tope_250_por_pedido(nodb):
    from flask import Flask

    from core.hotviews import registry
    from core.hotviews.api import NRS_IDS_CAP, hot_bp
    g = _snapshot_gen()
    registry.publish(g)
    app = Flask(__name__)
    app.register_blueprint(hot_bp)
    ids = [n['id'] for n in g.views['graph'].nodes][:400]
    d = app.test_client().get('/api/hot/nrs?ids=' + ','.join(ids)).get_json()['data']
    assert NRS_IDS_CAP == 250 and d['n'] + len(d['unknown_ids']) == 250
    # la línea de 250 ids reales cabe en el límite de gunicorn (4.094 caracteres)
    from urllib.parse import quote
    longest = sorted(ids, key=len, reverse=True)[:250]
    assert len('GET /api/hot/nrs?ids=' + quote(','.join(longest)) + ' HTTP/1.1') < 4094


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_hotclient_parte_el_lote_en_trozos_de_200_y_junta_la_respuesta():
    js = r"""
const fs = require('fs'), vm = require('vm');
const calls = [];
const ctx = { console, Date, Math, JSON, Promise, setTimeout, clearTimeout, Object, Array, String, Number, isFinite,
  navigator: { onLine: true },
  fetch: (url) => { calls.push(url); const ids = decodeURIComponent((/ids=([^&]*)/.exec(url) || [])[1] || '').split(',').filter(Boolean);
    const values = {}; ids.forEach(i => { if (!i.startsWith('X')) values[i] = 40; });
    return Promise.resolve({ ok: true, status: 200, headers: { get: () => null },
      json: () => Promise.resolve({ data: { values, n: Object.keys(values).length, unknown_ids: ids.filter(i => i.startsWith('X')), fund_version: 3 },
                                    view: { generation: 'g1' } }) }); } };
ctx.window = ctx; ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1] + '/engine/hotclient.js', 'utf8'), ctx);
const ids = []; for (let i = 0; i < 450; i++) ids.push((i % 50 === 0 ? 'X' : 'N') + i);
ctx.KhipuHot.nrs(ids).then(r => {
  process.stdout.write(JSON.stringify({ ok: r.ok, n: r.data.n, unknown: r.data.unknown_ids.length, fv: r.data.fund_version,
    calls: calls.length, maxIds: Math.max(...calls.map(u => decodeURIComponent(/ids=([^&]*)/.exec(u)[1]).split(',').length)) }));
});
"""
    p = subprocess.run([NODE, '-e', js, ROOT], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr[-1500:]
    o = json.loads(p.stdout)
    assert o == {'ok': True, 'n': 441, 'unknown': 9, 'fv': 3, 'calls': 3, 'maxIds': 200}, o


# ── progreso del chat ──────────────────────────────────────────────────────────────────────────────────────────────
def _blk():
    return {'id': 'b1', 'type': 'callout', 'state': 'ready', 'prov': {'kind': 'tool', 'name': 'get_research', 'call': 0},
            'data': {'variant': 'info', 'origin': 'tool', 'text': {'es': 'x', 'en': 'x'}}}


def test_progreso_sin_provisionales_es_el_json_de_siempre():
    from core import khipu_chat as kc
    kc.progress_begin('lj-plain')
    kc.progress_add('lj-plain', 'get_company', {'id_or_ticker': 'TSMC'})
    out = kc.progress_get('lj-plain')
    assert 'seq' not in out and 'ui' not in out and out['agents']
    assert set(out) == {'req_id', 'done', 'elapsed_ms', 'phase', 'agents'}


def test_bloques_provisionales_solo_para_el_navegador_que_pregunto():
    from core import khipu_chat as kc
    me, other = kc._owner_tag('k' * 24), kc._owner_tag('z' * 24)
    assert me and other and me != other and kc._owner_tag('corta') == ''
    kc.progress_begin('lj-own', ui={'send': True, 'lang': 'es'}, owner=me)
    kc.progress_add('lj-own', 'get_research', {})
    kc.progress_ui('lj-own', [_blk()])
    assert kc.progress_get('lj-own', owner=me)['ui']['blocks']
    for who in (other, '', None):
        o = kc.progress_get('lj-own', owner=who)
        assert 'ui' not in o and o['agents'] and 'seq' in o, who          # los agentes sí; las cifras no
    # sin llave al preguntar: como antes (cualquiera con el id)
    kc.progress_begin('lj-anon', ui={'send': True, 'lang': 'es'}, owner='')
    kc.progress_ui('lj-anon', [_blk()])
    assert kc.progress_get('lj-anon', owner=other)['ui']['blocks']


def test_ruta_de_progreso_usa_la_cabecera_del_navegador():
    import server
    from core import khipu_chat as kc
    key = 'navegador-de-prueba-0123456789'
    kc.progress_begin('lj-route', ui={'send': True, 'lang': 'es'}, owner=kc._owner_tag(key))
    kc.progress_ui('lj-route', [_blk()])
    c = server.app.test_client()
    assert c.get('/api/khipu/chat/progress/lj-route', headers={'X-Khipu-Owner': key}).get_json().get('ui')
    assert 'ui' not in c.get('/api/khipu/chat/progress/lj-route').get_json()
    assert 'ui' not in c.get('/api/khipu/chat/progress/lj-route', headers={'X-Khipu-Owner': 'otra-llave-0123456789'}).get_json()


def test_el_cliente_manda_la_llave_al_preguntar_y_al_sondear():
    with open(os.path.join(ROOT, 'engine', 'khipu_chat.js'), encoding='utf-8') as fh:
        js = fh.read()
    assert "headers: { 'Content-Type': 'application/json', 'X-Khipu-Owner': _owner() }, body: JSON.stringify(body)" in js
    assert "headers: { Accept: 'application/json', 'X-Khipu-Owner': _owner() }" in js


def test_el_diagnostico_cuenta_los_parciales():
    from core import genui
    genui.reset_stats()
    genui.note_progressive(3, 9.5, held=1)
    genui.note_progressive(0, 0)                               # una respuesta sin parciales no cuenta
    p = genui.stats()['progressive']
    assert p == {'answers': 1, 'builds': 3, 'held': 1, 'ms_p50': 9.5, 'ms_p95': 9.5}
    genui.reset_stats()
    assert genui.stats()['progressive']['answers'] == 0


# ── 🩺 y /api/matrix/parity ──────────────────────────────────────────────────────────────────────────────────────────
def test_gobernanza_avisa_si_matrix_engine_dense_no_se_obedece(monkeypatch):
    import server
    from matrix import engine as E
    monkeypatch.setattr(E, 'dense_refused', lambda: {'es': 'MATRIX_ENGINE=dense no se obedece con 5000 nodos',
                                                     'en': 'MATRIX_ENGINE=dense is not obeyed with 5000 nodes'})
    card = server._diag_gobernanza()
    assert 'MATRIX_ENGINE=dense no se obedece' in card['detail'] and 'is not obeyed' in card['detail_en']
    assert card['ok'] is False
    monkeypatch.setattr(E, 'dense_refused', lambda: None)
    assert 'MATRIX_ENGINE' not in server._diag_gobernanza()['detail']


@pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
def test_parity_no_arma_el_denso_por_encima_del_tope(monkeypatch):
    import server
    from core import http as h
    from matrix import engine as E
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    try:
        with session_scope() as s:
            for i in range(4):
                apply_event(s, 'ObjectCreated', {'label': f'P{i}', 'type': 'Company'}, valid_from='2000-01-01',
                            source='test', actor='pytest', object_id=f'LJP{i}')
            for a, b in (('LJP0', 'LJP1'), ('LJP1', 'LJP2'), ('LJP2', 'LJP3')):
                apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 2.0}, valid_from='2000-01-01',
                            source='test', actor='pytest', object_id=a, target_id=b)
        with h._rate_lock:
            h._rate_buckets.clear()
        c = server.app.test_client()
        built = []
        real = E.build_matrices

        def spy(s, *a, **k):
            built.append(k.get('sparse'))
            return real(s, *a, **k)
        monkeypatch.setattr(E, 'build_matrices', spy)
        monkeypatch.setattr(E, 'DENSE_MAX_NODES', 2)
        d = c.get('/api/matrix/parity').get_json()
        assert d['available'] is False and d['code'] == 'dense_refused' and d['reason_en'] and built == [True]
        monkeypatch.setattr(E, 'DENSE_MAX_NODES', 2000)
        built.clear()
        d = c.get('/api/matrix/parity').get_json()
        assert d['available'] is True and d['within_tolerance'] is True and built == [True, False]
    finally:
        with h._rate_lock:
            h._rate_buckets.clear()
        Base.metadata.drop_all(engine)


# ── tensor ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_cap_en_riesgo_es_la_suma_exacta():
    import math

    import scipy.sparse as sp

    from matrix import tensor as T
    # 0,1·(9,85 + …) — la suma de BLAS daba 9,850000000000001 → «9,9»; fsum da la suma correctamente redondeada
    m = sp.csc_matrix(np.array([[0.1, 0.0], [0.7, 0.0], [0.2, 1.0]]))
    cap = np.array([30.5, 7.5, 18.0])
    got = T._colsum_exact(m, cap)
    assert got.tolist() == [math.fsum([0.1 * 30.5, 0.7 * 7.5, 0.2 * 18.0]), 18.0]
    rng = np.random.default_rng(3)
    M = sp.random(300, 300, density=0.05, format='csc', random_state=3)
    w = rng.lognormal(2, 2, 300)
    assert np.allclose(T._colsum_exact(M, w), np.asarray(M.T @ w).ravel(), rtol=1e-12, atol=1e-9)


def test_find_similar_entities_ordena_como_peers(nodb):
    from matrix import tensor
    from mcp_server import ops
    m = tensor.model()
    for nid in ('AMD', 'TSMC', 'Nvidia'):
        out = ops.t_find_similar_entities(None, nid, k=8, space='combined')
        peers = tensor.peers(nid, m=m, n=8)
        assert [r['id'] for r in out['results']] == [p['id'] for p in peers], nid
        assert all(r['id'] != out['id'] for r in out['results'])
