"""tests/test_bitemporal.py — INFRA_OPERATIVA paso 23: G(t, κ) bitemporal.

t = fecha de VALIDEZ (as_of), κ = lo que Khipus había REGISTRADO (known_at: graph_version o instante).

  · un hecho corregido después: as_of t con κ ANTES de la corrección muestra el valor viejo; DESPUÉS, el nuevo
    (props de objeto, severidad de un factor → fragilidad, estado de un vínculo);
  · un vínculo retractado deja de verse a partir del κ de la retracción (y se veía antes);
  · un nodo todavía no creado (en t o en κ) no aparece, ni sus vínculos;
  · Δθ en diff_graph; known_at ISO ↔ graph_version; eventos sin versión (txid NULL) por recorded_at;
  · PARIDAD: known_at = ahora da EXACTAMENTE lo de hoy (as_of_graph, build_matrices, active_factors y la vista
    AsOf contra la vista viva en TODOS los choques);
  · API (/api/ontology/graph|graph/diff|objects/<id>|history|timeline, /api/hot/impact) y MCP get_ontology_object.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')

G = '2000-01-01'


def _ev(s, et, payload, oid, tgt=None, vf=G, vt=None):
    from ontology.service import apply_event
    return apply_event(s, et, payload, valid_from=vf, valid_to=vt, source='test', actor='pytest',
                       object_id=oid, target_id=tgt)


def _gv():
    from ontology import bitemporal
    from ontology.db import session_scope
    with session_scope() as s:
        return bitemporal.current_version(s)


def _clock():
    from sqlalchemy import text

    from ontology.db import session_scope
    with session_scope() as s:
        return s.execute(text('SELECT clock_timestamp()')).scalar()


@pytest.fixture(scope='module')
def w():
    """Mundo con historia: cada bloque es UNA transacción (una versión del grafo)."""
    from core.hotviews import registry
    from core.hotviews.views import asof
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    registry.reset()
    asof.reset()
    k = {}
    with session_scope() as s:                       # v1: el universo
        for oid in ('BT_A', 'BT_B', 'BT_C', 'BT_X'):
            _ev(s, 'ObjectCreated', {'label': oid, 'type': 'Company', 'properties': {'country': 'US'}}, oid)
        _ev(s, 'ObjectCreated', {'label': 'Factor F', 'type': 'Factor', 'properties': {'severity': 3.0}}, 'BT_F')
        _ev(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 5}, 'BT_A', 'BT_B')
        _ev(s, 'LinkCreated', {'rel_type': 'fab', 'weight': 4}, 'BT_B', 'BT_X')
        k['ac'] = _ev(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 3}, 'BT_A', 'BT_C')
        _ev(s, 'LinkCreated', {'rel_type': 'affects', 'weight': 0.5}, 'BT_F', 'BT_B')
    k['v1'] = _gv()
    k['t1'] = _clock()
    with session_scope() as s:                       # v2: correcciones retroactivas (valid_from = el de entonces)
        _ev(s, 'ObjectUpdated', {'properties': {'country': 'TW'}}, 'BT_A')
        _ev(s, 'ObjectUpdated', {'properties': {'severity': 8.0}}, 'BT_F', vf='2001-01-01')
        _ev(s, 'LinkRemoved', {'rel_type': 'supply', 'properties': {'retracts_event_id': str(k['ac'].id)}},
            'BT_A', 'BT_C')
    k['v2'] = _gv()
    k['t2'] = _clock()
    with session_scope() as s:                       # v3: un nodo nuevo (y otro que "nace" en 2025 con un vínculo viejo)
        _ev(s, 'ObjectCreated', {'label': 'BT_E', 'type': 'Company', 'properties': {}}, 'BT_E')
        _ev(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 2}, 'BT_E', 'BT_A')
        _ev(s, 'ObjectCreated', {'label': 'BT_D', 'type': 'Company', 'properties': {}}, 'BT_D', vf='2025-06-01')
        _ev(s, 'LinkCreated', {'rel_type': 'cloud', 'weight': 2}, 'BT_D', 'BT_B')
    k['v3'] = _gv()
    with session_scope() as s:                       # sin versión: un objeto NO económico (nota) — no mueve κ
        _ev(s, 'ObjectCreated', {'label': 'nota', 'type': 'Annotation', 'properties': {}}, 'BT_NOTE')
    k['v_note'] = _gv()
    assert k['v1'] < k['v2'] < k['v3'] == k['v_note']
    yield k
    registry.reset()
    asof.reset()
    Base.metadata.drop_all(engine)


def _links(g):
    return {(l['source'], l['target'], l['rel_type']) for l in g['links']}


# ── semántica ───────────────────────────────────────────────────────────────────────────────────────────────
def test_hecho_corregido_despues_viejo_antes_nuevo_despues(w):
    from ontology import bitemporal
    from ontology.db import session_scope
    with session_scope() as s:
        before = bitemporal.props_at(s, ids=['BT_A'], t='2020-01-01T00:00:00+00:00',
                                     known=bitemporal.resolve(s, w['v1']))['BT_A']
        after = bitemporal.props_at(s, ids=['BT_A'], t='2020-01-01T00:00:00+00:00',
                                    known=bitemporal.resolve(s, w['v2']))['BT_A']
    # corrección RETROACTIVA (valid_from = 2000, registrada en v2): en t=2020 era US según lo que se sabía en v1,
    # y TW según lo que se sabe desde v2
    assert before['properties']['country'] == 'US'
    assert after['properties']['country'] == 'TW'
    with session_scope() as s:
        now_old = bitemporal.props_at(s, ids=['BT_A'], known=bitemporal.resolve(s, w['v1']))['BT_A']
        now_new = bitemporal.props_at(s, ids=['BT_A'], known=bitemporal.resolve(s, w['v2']))['BT_A']
    assert now_old['properties']['country'] == 'US' and now_new['properties']['country'] == 'TW'


def test_factor_corregido_cambia_la_fragilidad_segun_kappa(w):
    from matrix import engine as E
    from ontology import bitemporal
    from ontology.db import session_scope
    t = '2020-01-01T00:00:00+00:00'
    with session_scope() as s:
        f1 = E.active_factors(s, as_of=t, known=bitemporal.resolve(s, w['v1']))
        f2 = E.active_factors(s, as_of=t, known=bitemporal.resolve(s, w['v2']))
        f_early = E.active_factors(s, as_of='2000-06-01T00:00:00+00:00', known=bitemporal.resolve(s, w['v2']))
    assert [f['severity'] for f in f1] == [3.0]
    assert [f['severity'] for f in f2] == [8.0]          # valid_from 2001 ≤ t, registrada en v2
    assert [f['severity'] for f in f_early] == [3.0]     # en 2000-06 todavía no regía
    with session_scope() as s:
        idx, _ = E.node_index(s, as_of=t, known=bitemporal.resolve(s, w['v1']))
    assert E.fragility(idx, f2)[idx['BT_B']] > E.fragility(idx, f1)[idx['BT_B']] > 1.0


def test_vinculo_retractado_invisible_despues_de_kappa(w):
    from ontology.db import session_scope
    from ontology.service import as_of_graph
    with session_scope() as s:
        g1 = as_of_graph(s, '2020-01-01', known_at=w['v1'])
        g2 = as_of_graph(s, '2020-01-01', known_at=w['v2'])
        live = as_of_graph(s, '2020-01-01')
    assert ('BT_A', 'BT_C', 'supply') in _links(g1)
    assert ('BT_A', 'BT_C', 'supply') not in _links(g2)
    assert ('BT_A', 'BT_C', 'supply') not in _links(live)       # retracción retroactiva: hoy tampoco
    assert g1['known_graph_version'] == w['v1'] and g1['known_mode'] == 'graph_version'


def test_nodo_no_creado_todavia_invisible(w):
    from ontology.db import session_scope
    from ontology.service import as_of_graph
    with session_scope() as s:
        g2 = as_of_graph(s, '2026-01-01', known_at=w['v2'])        # BT_E aún no registrado en κ=v2
        g3_2020 = as_of_graph(s, '2020-01-01', known_at=w['v3'])   # BT_D existe solo desde 2025-06
        g3 = as_of_graph(s, '2026-01-01', known_at=w['v3'])
        live_2020 = as_of_graph(s, '2020-01-01')
    ids2 = {n['id'] for n in g2['nodes']}
    assert 'BT_E' not in ids2 and ('BT_E', 'BT_A', 'supply') not in _links(g2)
    ids3 = {n['id'] for n in g3_2020['nodes']}
    assert 'BT_D' not in ids3 and ('BT_D', 'BT_B', 'cloud') not in _links(g3_2020)
    assert g3_2020['counts']['links_without_node'] == 1
    assert ('BT_D', 'BT_B', 'cloud') in _links(live_2020)            # el camino de siempre no mira existencia
    assert {'BT_D', 'BT_E'} <= {n['id'] for n in g3['nodes']}
    from matrix import engine as E
    from ontology import bitemporal
    with session_scope() as s:
        idx, _ = E.node_index(s, as_of='2020-01-01', known=bitemporal.resolve(s, w['v3']))
        idx_v2, _ = E.node_index(s, known=bitemporal.resolve(s, w['v2']))
    assert 'BT_D' not in idx and 'BT_E' in idx and 'BT_E' not in idx_v2


def test_known_at_iso_equivale_a_la_version_y_txid_nulo_por_recorded_at(w):
    from ontology import bitemporal
    from ontology.db import session_scope
    with session_scope() as s:
        k = bitemporal.resolve(s, w['t1'].isoformat())
        assert k.gv == w['v1'] and k.mode == 'time' and k.key() == bitemporal.resolve(s, w['v1']).key()
        assert bitemporal.resolve(s, f'g{w["v2"]}').gv == w['v2']
        assert bitemporal.resolve(s, 'now') is None
        with pytest.raises(bitemporal.KnownAtError) as e:
            bitemporal.resolve(s, w['v3'] + 50)
        assert 'todavía no existe' in e.value.es and 'does not exist yet' in e.value.en
        with pytest.raises(bitemporal.KnownAtError):
            bitemporal.resolve(s, 'ayer por la tarde')
        # la nota (transacción NO económica, sin versión) se rige por recorded_at
        assert 'BT_NOTE' not in bitemporal.props_at(s, known=bitemporal.resolve(s, w['t2'].isoformat()))
        assert 'BT_NOTE' in bitemporal.props_at(s, known=bitemporal.resolve(s, w['v3']))


def test_eventos_sin_txid_cuentan_por_recorded_at(w):
    """Eventos anteriores a la migración del paso 1 (txid NULL): visibles si recorded_at ≤ κ.ts."""
    import uuid
    from datetime import datetime, timezone

    from sqlalchemy import text

    from ontology import bitemporal
    from ontology.db import session_scope
    with session_scope() as s:
        s.execute(text("INSERT INTO events (id, event_type, object_id, payload, valid_from, recorded_at, source, actor, "
                       "txid) VALUES (:id, 'ObjectCreated', 'BT_OLD', CAST(:p AS jsonb), :vf, :rec, 'test', 'pytest', "
                       "NULL)"), {'id': str(uuid.uuid4()), 'p': '{"label": "old", "type": "Annotation", "properties": {}}',
                                  'vf': datetime(2000, 1, 1, tzinfo=timezone.utc),
                                  'rec': datetime(2030, 1, 1, tzinfo=timezone.utc)})
    with session_scope() as s:
        assert 'BT_OLD' not in bitemporal.props_at(s, known=bitemporal.resolve(s, '2029-12-31'))
        assert 'BT_OLD' in bitemporal.props_at(s, known=bitemporal.resolve(s, '2030-01-02'))
        assert 'BT_OLD' in bitemporal.props_at(s, known=bitemporal.now_known(s))     # κ = hoy: todo lo sin versión


def test_delta_theta_en_diff_graph(w):
    from ontology.db import session_scope
    from ontology.service import diff_graph
    with session_scope() as s:
        d = diff_graph(s, '2000-06-01', '2002-01-01')
        d_v1 = diff_graph(s, '2000-06-01', '2002-01-01', known_at=w['v1'])
    ch = {c['id']: c['changes'] for c in d['changed']}
    assert ch['BT_F']['severity'] == {'from': 3.0, 'to': 8.0}
    assert d_v1['changed'] == [] and d_v1['known_graph_version'] == w['v1']
    assert d['counts']['changed'] == len(d['changed'])
    with session_scope() as s:
        d2 = diff_graph(s, '2025-01-01', '2026-01-01')
    assert {n['id'] for n in d2['nodes_added']} == {'BT_D'}


def test_historia_del_objeto_por_kappa(w):
    from ontology import bitemporal
    from ontology.db import session_scope
    from ontology.service import object_history
    with session_scope() as s:
        h1 = object_history(s, 'BT_A', known=bitemporal.resolve(s, w['v1']))
        h3 = object_history(s, 'BT_A')
    assert len(h1) < len(h3)
    assert not any(e.event_type == 'ObjectUpdated' for e in h1)


# ── paridad: κ = ahora == hoy ───────────────────────────────────────────────────────────────────────────────
def test_paridad_known_now_igual_a_hoy(w):
    import numpy as np

    from matrix import engine as E
    from ontology import bitemporal
    from ontology.db import session_scope
    from ontology.service import as_of_graph
    with session_scope() as s:
        now_k = bitemporal.now_known(s)
        for t in ('2026-01-01', None):
            a = as_of_graph(s, t)
            b = as_of_graph(s, t, known_at=now_k)
            assert _links(a) == _links(b), t
            assert sorted(a['links'], key=lambda l: l['event_id']) == sorted(b['links'], key=lambda l: l['event_id'])
            assert b['counts']['links_without_node'] == 0
        # única diferencia buscada (DT-M2): el vínculo de un nodo que en 2020 todavía no existía
        a, b = as_of_graph(s, '2020-01-01'), as_of_graph(s, '2020-01-01', known_at=now_k)
        assert _links(a) - _links(b) == {('BT_D', 'BT_B', 'cloud')} and _links(b) <= _links(a)
        assert b['counts']['links_without_node'] == 1
        m0, idx0, ids0 = E.build_matrices(s)
        m1, idx1, ids1 = E.build_matrices(s, known=now_k)
        assert ids0 == ids1
        for r in m0:
            a, b = m0[r], m1[r]
            a = a.toarray() if hasattr(a, 'toarray') else a
            b = b.toarray() if hasattr(b, 'toarray') else b
            assert np.array_equal(a, b), r
        f0 = sorted((f['id'], f['severity'], sorted(f['members'].items())) for f in E.active_factors(s))
        f1 = sorted((f['id'], f['severity'], sorted(f['members'].items())) for f in E.active_factors(s, known=now_k))
        assert f0 == f1


def test_vista_asof_kappa_ahora_igual_a_la_viva_en_todos_los_choques(w):
    from core.hotviews import source
    from core.hotviews.views import asof, graph_core, impact
    asof.reset()
    live = source.load_pg()
    lc = graph_core.build(live)
    li = impact.build(lc)
    g, meta = asof.get(None, None)
    ac, ai = g.views['graph_core'], g.views['impact']
    assert meta['cache'] == 'miss' and ac.ids == lc.ids and ai.sources == li.sources
    assert [o for o in li.sources if li.victims[o] != ai.victims[o]] == []
    assert ai.content_sha == li.content_sha
    g2, meta2 = asof.get(None, str(w['v3']))
    assert meta2['cache'] == 'hit' and g2 is g                       # κ canónico = la versión
    assert asof.stats()['entries'] == 1


def test_vista_asof_del_pasado_distinta_y_lru(w):
    from core.hotviews.views import asof
    asof.reset()
    g1, m1 = asof.get('2020-01-01', w['v1'])
    imp1 = g1.views['impact']
    assert m1['known_graph_version'] == w['v1'] and 'BT_C' in dict(zip(*imp1.victims['BT_A'][:2]))
    g2, _ = asof.get('2020-01-01', w['v2'])
    assert 'BT_C' not in dict(zip(*g2.views['impact'].victims['BT_A'][:2]))
    old = asof.LRU_MAX
    asof.LRU_MAX = 2
    try:
        asof.get('2021-01-01', w['v1'])
        assert asof.stats()['entries'] == 2
        _, m = asof.get('2020-01-01', w['v1'])
        assert m['cache'] == 'miss'                                  # desalojado (LRU)
    finally:
        asof.LRU_MAX = old


# ── API y MCP ───────────────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope='module')
def client(w):
    import server
    return server.app.test_client()


def test_api_graph_known_at(client, w):
    r = client.get(f'/api/ontology/graph?as_of=2020-01-01&known_at={w["v1"]}')
    assert r.status_code == 200
    d = r.get_json()
    assert d['known_graph_version'] == w['v1'] and ('BT_A', 'BT_C', 'supply') in _links(d)
    r = client.get('/api/ontology/graph?known_at=pronto')
    assert r.status_code == 400 and r.get_json()['error_en'].startswith('invalid known_at')
    live = client.get('/api/ontology/graph?as_of=2020-01-01').get_json()
    assert 'known_graph_version' not in live                       # sin known_at: la respuesta de siempre
    d = client.get(f'/api/ontology/graph/diff?from=2000-06-01&to=2002-01-01&known_at={w["v2"]}').get_json()
    assert any(c['id'] == 'BT_F' for c in d['changed'])
    bt = client.get('/api/ontology/status').get_json()['bitemporal']
    assert bt['object_versions_threshold'] == 20_000 and bt['object_versions_recommended'] is False


def test_api_objeto_historia_y_timeline_en_kappa(client, w):
    d = client.get(f'/api/ontology/objects/BT_A?known_at={w["v1"]}').get_json()
    assert d['properties']['country'] == 'US' and d['method'] == 'props_at@1' and d['valid_from_known'] is False
    assert client.get('/api/ontology/objects/BT_A').get_json()['properties']['country'] == 'TW'
    assert client.get(f'/api/ontology/objects/BT_E?known_at={w["v2"]}').status_code == 404
    h = client.get(f'/api/ontology/objects/BT_A/history?known_at={w["v1"]}').get_json()
    assert h['known_graph_version'] == w['v1'] and h['count'] < client.get('/api/ontology/objects/BT_A/history').get_json()['count']
    tl = client.get(f'/api/ontology/objects/BT_A/timeline?news=0&known_at={w["v1"]}').get_json()
    assert tl['known_graph_version'] == w['v1']
    assert client.get('/api/ontology/objects/BT_A/timeline?known_at=xx').status_code == 400


def test_api_hot_impact_as_of_known_at(client, w):
    from core.hotviews.views import asof
    asof.reset()
    r = client.get(f'/api/hot/impact/BT_A?as_of=2020-01-01&known_at={w["v1"]}')
    assert r.status_code == 200
    d = r.get_json()
    assert d['view']['source'] == 'asof' and d['view']['known_graph_version'] == w['v1']
    assert d['view']['stale'] is False and d['view']['cache'] == 'miss'
    assert 'BT_C' in {v['id'] for v in d['data']['victims']}
    d2 = client.get(f'/api/hot/impact/BT_A?as_of=2020-01-01&known_at={w["v1"]}').get_json()
    assert d2['view']['cache'] == 'hit' and d2['data'] == d['data']
    live = client.get('/api/hot/impact/BT_A').get_json()
    assert live['view']['source'] == 'pg' and 'BT_C' not in {v['id'] for v in live['data']['victims']}
    assert client.get('/api/hot/impact/BT_A?known_at=999999').status_code == 400
    st = client.get('/api/hot/status').get_json()['data']
    assert st['asof']['entries'] >= 1


def test_mcp_get_ontology_object_en_kappa(w):
    from mcp_server import contract, tools
    d = tools.t_get_ontology_object(None, id='BT_A', known_at=str(w['v1']))
    assert d['object']['properties']['country'] == 'US' and d['known_graph_version'] == w['v1']
    assert any(l['target'] == 'BT_C' for l in d['active_links']['outgoing'])
    now = tools.t_get_ontology_object(None, id='BT_A')
    assert now['object']['properties']['country'] == 'TW'
    with pytest.raises(tools.ToolError) as e:
        tools.t_get_ontology_object(None, id='BT_E', known_at=str(w['v2']))
    assert e.value.code == 'not_found'
    with pytest.raises(tools.ToolError) as e:
        tools.t_get_ontology_object(None, id='BT_A', known_at='mañana')
    assert e.value.code == 'invalid_params'
    out = contract.apply('get_ontology_object', d)
    assert out['known_at'] == d['known_at']           # el contrato respeta el κ de la herramienta
