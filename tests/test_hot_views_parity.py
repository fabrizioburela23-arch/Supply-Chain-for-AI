"""tests/test_hot_views_parity.py — INFRA_OPERATIVA paso 4: las vistas dan EXACTAMENTE los números del kernel.

  · `propagate_many` (lote) == `propagate` (bucle) en TODOS los choques de un nodo del catálogo (937 empresas
    + objetos de ontología), impactos Y salto de primera llegada — igualdad exacta, no aproximada;
  · la vista Impact reproduce compute_metrics (cascade_size, rangos, PageRank) y /api/matrix/metrics
    delegado devuelve el MISMO payload que el cálculo directo;
  · en Postgres, las matrices/factores/fragilidad de GraphCore == build_matrices/active_factors/fragility;
  · el grado de flujo de la vista es la regla del NRS (pares distintos, vocabulary.flow_degree).
"""
import os
import random
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


@pytest.fixture(scope='module')
def snap():
    from core.hotviews import source
    from core.hotviews.views import graph_core, impact
    data = source.load_snapshot()
    core = graph_core.build(data)
    return data, core, impact.build(core)


def test_propagate_many_es_identico_al_bucle_en_todos_los_choques_del_catalogo(snap):
    from matrix import engine as E
    data, core, _ = snap
    assert len(core.ids) >= 937
    many = E.propagate_many(core.mats, core.idx, core.ids, core.ids, frag=core.frag, dt=core.dt)
    bad = []
    for oid in core.ids:
        imp, order = E.propagate(core.mats, core.idx, core.ids, [oid], frag=core.frag, dt=core.dt)
        if imp != many[oid][0] or {o['id']: o['hop'] for o in order} != many[oid][1]:
            bad.append(oid)
    assert bad == [], f'{len(bad)} choques distintos: {bad[:10]}'


def test_sin_fragilidad_y_con_otros_parametros_tambien_identico(snap):
    from matrix import engine as E
    _, core, _ = snap
    sample = random.Random(7).sample(core.ids, 120)
    for kw in ({'damping': 0.8, 'max_hops': 9}, {'magnitude': 0.4, 'threshold': 0.02}, {'nonlinear': True}):
        many = E.propagate_many(core.mats, core.idx, core.ids, sample, dt=core.dt, **kw)
        for oid in sample:
            imp, order = E.propagate(core.mats, core.idx, core.ids, [oid], dt=core.dt, **kw)
            assert imp == many[oid][0], (kw, oid)
            assert {o['id']: o['hop'] for o in order} == many[oid][1], (kw, oid)


def test_la_vista_impact_reproduce_compute_metrics(snap):
    from matrix import engine as E
    _, core, view = snap
    # compute_metrics sobre las mismas matrices (su núcleo, sin la base)
    pr = E.pagerank(core.agg)
    ref = {}
    for oid, i in core.idx.items():
        if core.out_w[i] == 0 and core.in_w[i] == 0:
            continue
        imp, _ = E.propagate(core.mats, core.idx, core.ids, [oid], frag=core.frag, dt=core.dt)
        ref[oid] = {'out_weight': round(float(core.out_w[i]), 2), 'in_weight': round(float(core.in_w[i]), 2),
                    'cascade_size': max(0, sum(1 for v in imp.values() if v >= 1.0) - 1),
                    'pagerank': round(float(pr[i]), 6)}
    for rank, (oid, m) in enumerate(sorted(ref.items(), key=lambda kv: -kv[1]['cascade_size']), 1):
        m['chokepoint_rank'] = rank
    for rank, (oid, m) in enumerate(sorted(ref.items(), key=lambda kv: -kv[1]['pagerank']), 1):
        m['pagerank_rank'] = rank
    assert view.metrics == ref
    # víctimas precalculadas == propagate
    for oid in random.Random(3).sample(view.sources, 60):
        imp, order = E.propagate(core.mats, core.idx, core.ids, [oid], frag=core.frag, dt=core.dt)
        ids_, pct, hop = view.victims[oid]
        assert dict(zip(ids_, pct)) == imp
        assert {k: h for k, h in zip(ids_, hop) if h} == {o['id']: o['hop'] for o in order}


def test_ranking_por_suma_y_por_conteo(snap):
    _, core, view = snap
    sums = [view.stats[k]['sum_impact'] for k in view.by_sum]
    counts = [view.stats[k]['reach_1'] for k in view.by_count]
    assert sums == sorted(sums, reverse=True) and counts == sorted(counts, reverse=True)
    tsmc = view.stats['TSMC']
    assert view.by_sum[0] == 'TSMC' and tsmc['reach_1'] > 200 and tsmc['sum_impact'] > tsmc['reach_10'] / 10


def test_grado_de_flujo_en_pares_distintos(snap):
    from ontology import vocabulary as vocab
    data, core, _ = snap
    assert core.flow_degree == vocab.flow_degree(data.flow_links)
    # partner/invest no cuentan y un par repetido cuenta una vez
    assert vocab.flow_degree([{'source': 'a', 'target': 'b', 'type': 'supply'},
                              {'source': 'a', 'target': 'b', 'type': 'fab'},
                              {'source': 'a', 'target': 'c', 'type': 'partner'}]) == {'a': 1, 'b': 1}


# ── Postgres: la vista == las funciones de matrix.engine sobre la MISMA base ────
@pytest.fixture(scope='module')
def pg():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    rnd = random.Random(11)
    ids = [f'HP_{i:02d}' for i in range(60)]
    rels = ['supply', 'fab', 'cloud', 'license', 'partner', 'invest', 'owns']
    with session_scope() as s:
        for oid in ids:
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company', 'properties': {'sector': 'x'}},
                        valid_from='2000-01-01', source='test', actor='pytest', object_id=oid)
        for _ in range(220):
            a, b = rnd.sample(ids, 2)
            props = {'rel_label': 'posible' if rnd.random() < 0.2 else 'ok'}
            if rnd.random() < 0.15:
                props['confidence'] = 0.5
            apply_event(s, 'LinkCreated', {'rel_type': rnd.choice(rels), 'weight': rnd.choice([1, 2, 3, 4, 5, 6]),
                                           'properties': props},
                        valid_from='2000-01-01', source='test', actor='pytest', object_id=a, target_id=b)
        apply_event(s, 'ObjectCreated', {'label': 'F', 'type': 'Factor', 'properties': {'severity': 3.0}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='HP_FX')
        for m in ids[:5]:
            apply_event(s, 'LinkCreated', {'rel_type': 'affects', 'weight': 0.6}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id='HP_FX', target_id=m)
    from core.hotviews import registry
    registry.reset()
    yield engine
    registry.reset()
    Base.metadata.drop_all(engine)


@needs_db
def test_graphcore_en_postgres_es_build_matrices(pg):
    from core.hotviews import source
    from core.hotviews.views import graph_core
    from matrix import engine as E
    from ontology.db import session_scope
    data = source.load_pg()
    core = graph_core.build(data)
    with session_scope() as s:
        mats, idx, ids = E.build_matrices(s)
        factors = E.active_factors(s)
    assert data.source == 'pg' and ids == core.ids and idx == core.idx
    for r in mats:
        a, b = mats[r], core.mats[r]
        a = a.toarray() if hasattr(a, 'toarray') else a
        b = b.toarray() if hasattr(b, 'toarray') else b
        assert np.array_equal(a, b), r
    assert [f['id'] for f in factors] == [f['id'] for f in core.factors]
    assert np.array_equal(E.fragility(idx, factors), core.frag)


@needs_db
def test_metrics_delegado_es_identico_al_calculo_directo(pg):
    import matrix.api as M
    import server
    from matrix import engine as E
    from ontology.db import session_scope
    c = server.app.test_client()
    d = c.get('/api/matrix/metrics').get_json()
    assert d['view']['source'] == 'pg' and d['view']['stale'] is False
    with session_scope() as s:
        metrics, factors = E.compute_metrics(s)
    assert d['metrics'] == metrics and d['nodes'] == len(metrics)
    assert d['factors_active'] == [f['label'] for f in factors]
    top = sorted(metrics.items(), key=lambda kv: kv[1]['chokepoint_rank'])[:25]
    assert d['chokepoints_top25'] == [{'id': k, **v} for k, v in top]
    # y /impact delegado == propagate sobre build_matrices (mismo kernel, misma versión)
    with session_scope() as s:
        mats, idx, ids = E.build_matrices(s)
        frag = E.fragility(idx, E.active_factors(s))
    for oid in ('HP_00', 'HP_07', 'HP_33'):
        r = c.post('/api/matrix/impact', json={'shock': [oid]}).get_json()
        imp, order = E.propagate(mats, idx, ids, [oid], frag=frag)
        assert r['impacts'] == imp and r['cascade'] == order and r['view']['source'] == 'pg'
    assert M.HOT_WAIT_S > 0


# ════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Paso 14 (INFRA_OPERATIVA §4.2 V3 Card + NRS, V4 Quote, V6 GeoRisk, AlertIndex): las vistas nuevas dan
# EXACTAMENTE lo que daban los cálculos directos que reemplazan.
# ════════════════════════════════════════════════════════════════════════════════════════════════════════════
@pytest.fixture(scope='module')
def cardv(monkeypatch_module=None):
    import ontology.db as odb
    from core.hotviews import builder, derived, hot, registry
    from core.hotviews.views import card
    real = odb.ontology_available
    odb.ontology_available = lambda: False
    registry.reset()
    hot.reset()
    derived.reset()
    try:
        g = builder.build_once()
        yield g, card.view(g)
    finally:
        odb.ontology_available = real
        registry.reset()
        hot.reset()
        derived.reset()


def test_card_nrs_es_la_formula_unica_en_todas_las_empresas(cardv, monkeypatch):
    import core.live_fundamentals as lf
    from core import world
    monkeypatch.setattr(lf, 'live_margin', lambda *_a, **_k: None)
    monkeypatch.setattr(lf, 'version', lambda: -7)        # fuerza recalcular con el margen del catálogo
    g, cv = cardv
    gv = g.views['graph']
    allv = cv.nrs_all()
    assert len(allv) == len(gv.nodes) >= 937
    bad = [n['id'] for n in gv.nodes if allv[n['id']]['total'] != world.client_nrs(n, gv.flow_degree.get(n['id'], 0))]
    assert bad == []
    t = allv['TSMC']
    assert t['total'] == min(100, max(0, int(t['geo'] + t['chain'] + t['market'] + t['fundamental'] +
                                             t['concentration'] + 0.5)))


def test_card_flujo_en_pares_distintos_y_relacionadas_aparte(cardv):
    from ontology import vocabulary as vocab
    g, cv = cardv
    gv = g.views['graph']
    flow = set(vocab.flow_relation_types())
    sup, cus, rel = {}, {}, {}
    for l in gv.links:
        s, t, typ = l['source'], l['target'], l.get('type') or 'supply'
        if s == t or s not in gv.by_id or t not in gv.by_id:
            continue
        if typ in flow:
            sup.setdefault(t, set()).add(s)
            cus.setdefault(s, set()).add(t)
        elif typ in ('partner', 'invest'):
            rel.setdefault(s, set()).add(t)
            rel.setdefault(t, set()).add(s)
    for oid, c in cv.cards.items():
        assert c['counts']['suppliers'] == len(sup.get(oid, ())), oid
        assert c['counts']['customers'] == len(cus.get(oid, ())), oid
        assert c['counts']['related'] == len(rel.get(oid, ())), oid
        ws = [x['w'] or 0 for x in c['top_suppliers']]
        assert ws == sorted(ws, reverse=True) and len(c['top_suppliers']) <= 5
        assert all(x['type'] in flow for x in c['top_suppliers'] + c['top_customers'])
        assert all(x['type'] in ('partner', 'invest') for x in c['related'])


def test_card_impacto_y_estructura_salen_de_las_vistas_de_la_misma_generacion(cardv):
    from matrix import tensor
    g, cv = cardv
    imp = g.views['impact']
    for oid in ('TSMC', 'Nvidia', 'ASML', 'Microsoft'):
        st = imp.stats[oid]
        c = cv.cards[oid]['impact']
        assert (c['reach_1'], c['reach_10'], c['sum_impact']) == (st['reach_1'], st['reach_10'], st['sum_impact'])
        assert c['rank_by_sum'] == imp.by_sum.index(oid) + 1
        m = cv.structure_model()
        assert cv.structure(oid) == tensor.structure(oid, m=m, top=5)


def test_mcp_y_chat_leen_el_nrs_de_la_tarjeta(cardv, monkeypatch):
    import core.live_fundamentals as lf
    import mcp_server.tools as T
    from core import khipu_chat
    monkeypatch.setattr(lf, 'live_margin', lambda *_a, **_k: None)
    g, cv = cardv
    out = T.t_get_company(None, 'TSMC', include_live=False)
    assert out['network_risk_score']['value'] == cv.nrs('TSMC')
    assert out['network_risk_score']['terms']['geo'] == cv.nrs_all()['TSMC']['geo']
    rk = khipu_chat.x_rank_companies(by='risk', limit=25)
    assert all(r['nrs'] == cv.nrs(r['id']) for r in rk['items'])


def test_mcp_get_company_cuenta_pares_distintos_como_la_tarjeta(cardv):
    """Revisión batch E: el MCP (y el chat local_fact, que lo resume) contaba ARISTAS de flujo (TSMC 95 clientes)
    mientras la tarjeta que lee la voz cuenta CONTRAPARTES distintas (78). Mismo número en TODAS las empresas."""
    import mcp_server.tools as T
    g, cv = cardv
    bad = []
    for oid in cv.cards:
        out = T.t_get_company(None, oid, include_live=False)
        c = cv.cards[oid]
        if out['counts'] != {k: c['counts'][k] for k in ('suppliers', 'customers', 'related')}:
            bad.append(oid)
            continue
        for k in ('top_suppliers', 'top_customers', 'related'):
            mine = [(x['id'], x['weight'] or 0) for x in out[k][:5]]
            theirs = [(x['id'], x['w'] or 0) for x in c[k]]
            if mine != theirs:
                bad.append((oid, k))
        ids = [x['id'] for x in out['top_customers']]
        assert len(ids) == len(set(ids)) and oid not in ids
    assert bad == []
    assert T.t_get_company(None, 'TSMC', include_live=False)['counts']['customers'] == cv.cards['TSMC']['counts'][
        'customers']


def test_api_card_y_nrs_con_sobre_etag_y_304(cardv):
    import server
    g, cv = cardv
    c = server.app.test_client()
    r = c.get('/api/hot/card/TSM?lang=en')
    assert r.status_code == 200
    d = r.get_json()
    assert d['data']['id'] == 'TSMC' and d['data']['lang'] == 'en' and d['view']['generation'] == g.id
    assert d['data']['nrs']['value'] == cv.nrs('TSMC') and d['data']['structure']['id'] == 'TSMC'
    et = r.headers['ETag']
    assert et.startswith('"card:') and r.headers['X-Khipu-Graph-Version'] == '0'
    assert c.get('/api/hot/card/TSM?lang=en', headers={'If-None-Match': et}).status_code == 304
    n = c.get('/api/hot/nrs?ids=TSMC,Nvidia,NoExiste&terms=1').get_json()['data']
    assert n['values'] == {'TSMC': cv.nrs('TSMC'), 'Nvidia': cv.nrs('Nvidia')} and n['unknown_ids'] == ['NoExiste']
    assert set(n['terms']['TSMC']) == {'geo', 'chain', 'market', 'fundamental', 'concentration', 'degree'}
    allv = c.get('/api/hot/nrs').get_json()['data']
    assert allv['n'] == len(cv.cards)
    assert c.get('/api/hot/card/NoExisteNada').status_code == 404


def test_quote_con_sello_no_inventa_y_marca_lo_viejo():
    from core.hotviews.views import quote
    fake = lambda syms: {'quotes': {'NVDA': {'close': 181.2, 'prev': 180.0, 'live': 181.2, 'src': 'finnhub',
                                             'as_of': '2026-10-13T14:00:00+00:00', 'age_seconds': 4},
                                    'OLD': {'close': 10.0, 'prev': 10.0, 'src': 'yahoo', 'as_of': 'x',
                                            'age_seconds': 7200}}, 'cached': False}
    out = quote.stamped(['NVDA', 'OLD', 'NADA'], fetch=fake)
    assert set(out) == {'NVDA', 'OLD'}
    assert out['NVDA']['px'] == 181.2 and out['NVDA']['stamp']['live'] is True and out['NVDA']['stamp']['src'] == 'finnhub'
    assert out['OLD']['stamp']['stale'] is True and out['OLD']['stamp']['live'] is False


def test_geo_vista_igual_al_escaneo_directo(cardv, monkeypatch):
    import core.world as W
    from core.hotviews.views import geo
    g, cv = cardv
    tsmc = W._graph()['by_id']['TSMC']
    ev = {'items': [{'id': 'p1', 'layer': 'policy', 'lat': 0, 'lon': 0, 'title': 'Export rule names TSMC',
                     'severity': 70, 'affected': ['TSMC', 'SMIC'], 'time': '2026-10-13T00:00:00Z', 'source': 'BIS'},
                    {'id': 'q1', 'layer': 'quakes', 'lat': tsmc['lat'], 'lon': tsmc['lng'], 'title': 'M6 quake',
                     'severity': 60, 'time': '2026-10-13T01:00:00Z', 'source': 'USGS'}],
          'sources': {'policy': {'ok': True, 'count': 1, 'as_of': 't1'}}}
    monkeypatch.setattr(W, 'world_events', lambda window='24h', wait=0, layers=None: ev)
    geo.reset()
    facts, wv = geo.facts(['TSMC', 'SMIC', 'Nvidia'])
    direct = W.entity_geo_risks(['TSMC', 'SMIC', 'Nvidia'], wait=0)
    assert facts == direct and facts['TSMC'] and wv
    assert all(len(v) <= 3 for v in facts.values())
    geo.reset()
