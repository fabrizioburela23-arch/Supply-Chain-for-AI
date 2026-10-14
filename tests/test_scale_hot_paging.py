"""tests/test_scale_hot_paging.py — EXPANSION_5K E1.7: paginación y campos a pedido, compatibles hacia atrás.

  · /api/hot/factors sin parámetros = EXACTAMENTE la respuesta de siempre (mismas claves, misma lista, mismo ETag);
    con limit/offset → una página + total/limit/offset (las páginas juntas = la lista completa); fields= recorta
    los campos; parámetros malos → 400 bilingüe; cada página con su propio ETag (nunca un 304 cruzado);
  · /api/matrix/metrics sin top = el cuerpo de siempre; ?top=N → `metrics` con los N primeros cuellos de botella
    (+ metrics_total/top), lo demás igual; no toca lo cacheado;
  · /api/hot/nrs acepta el lote como ids=a,b o ids=a&ids=b (mismo resultado) y lo revalida con ETag.
Sin base: las vistas salen del snapshot (mismo código).
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

FACTOR_KEYS = {'factors', 'count', 'rho', 'damping_rho', 'stable'}


@pytest.fixture
def app(monkeypatch):
    import ontology.db as odb
    import server
    from core import http as h
    from core.hotviews import builder, registry
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    registry.reset()
    g = builder.build_once()
    with h._rate_lock:
        h._rate_buckets.clear()
    yield server.app.test_client(), g
    registry.reset()
    with h._rate_lock:
        h._rate_buckets.clear()


def test_factors_sin_parametros_es_la_respuesta_de_siempre(app):
    from core.hotviews.views import graph_core
    c, g = app
    r = c.get('/api/hot/factors')
    assert r.status_code == 200
    d = r.get_json()['data']
    assert set(d) == FACTOR_KEYS                              # sin total/limit/offset
    core = g.views['graph_core']
    assert d['factors'] == graph_core.factors_payload(core) and d['count'] == len(core.factors)
    assert r.headers['ETag'] == f'"graph_core:{g.id}"'        # la etiqueta de siempre
    assert c.get('/api/hot/factors', headers={'If-None-Match': r.headers['ETag']}).status_code == 304


def test_factors_paginados_y_con_campos(app):
    from core.hotviews.views import graph_core
    c, g = app
    full = graph_core.factors_payload(g.views['graph_core'])
    assert len(full) > 20
    r = c.get('/api/hot/factors?limit=5&offset=3')
    d = r.get_json()['data']
    assert d['factors'] == full[3:8] and d['total'] == len(full) == d['count']
    assert d['limit'] == 5 and d['offset'] == 3
    et_full = c.get('/api/hot/factors').headers['ETag']
    assert r.headers['ETag'] != et_full                       # una página nunca revalida con la etiqueta completa
    assert c.get('/api/hot/factors?limit=5&offset=3', headers={'If-None-Match': et_full}).status_code == 200
    assert c.get('/api/hot/factors?limit=5&offset=3', headers={'If-None-Match': r.headers['ETag']}).status_code == 304
    # recorrer todas las páginas = la lista completa, en el mismo orden
    got, off = [], 0
    while True:
        page = c.get(f'/api/hot/factors?limit=7&offset={off}').get_json()['data']['factors']
        if not page:
            break
        got += page
        off += 7
    assert got == full
    only_off = c.get('/api/hot/factors?offset=10').get_json()['data']
    assert only_off['factors'] == full[10:] and only_off['limit'] is None and only_off['offset'] == 10
    # campos a pedido (id siempre va); también sin paginar
    d = c.get('/api/hot/factors?fields=severity,label&limit=3').get_json()['data']
    assert [set(f) for f in d['factors']] == [{'id', 'severity', 'label'}] * 3
    assert [f['severity'] for f in d['factors']] == [f['severity'] for f in full[:3]]
    d = c.get('/api/hot/factors?fields=id').get_json()['data']
    assert [f['id'] for f in d['factors']] == [f['id'] for f in full] and 'total' not in d


@pytest.mark.parametrize('qs, param', [('limit=0', 'limit'), ('limit=abc', 'limit'), ('limit=100000', 'limit'),
                                       ('offset=-1', 'offset'), ('offset=1.5', 'offset'),
                                       ('fields=id,secreto', 'fields')])
def test_factors_parametros_malos_400_bilingue(app, qs, param):
    c, _g = app
    r = c.get(f'/api/hot/factors?{qs}')
    assert r.status_code == 400
    d = r.get_json()
    assert d['param'] == param and d['error'] and d['error_en'] and d['error'] != d['error_en']


def test_nrs_lote_por_coma_o_repetido(app):
    c, _g = app
    a = c.get('/api/hot/nrs?ids=TSMC,Nvidia,NoExiste')
    b = c.get('/api/hot/nrs?ids=TSMC&ids=Nvidia&ids=NoExiste')
    da, db_ = a.get_json()['data'], b.get_json()['data']
    assert da['values'] == db_['values'] and set(da['values']) == {'TSMC', 'Nvidia'}
    assert da['unknown_ids'] == db_['unknown_ids'] == ['NoExiste'] and da['n'] == 2
    et = a.headers.get('ETag')
    assert et and et == b.headers.get('ETag')
    assert c.get('/api/hot/nrs?ids=TSMC,Nvidia,NoExiste', headers={'If-None-Match': et}).status_code == 304
    other = c.get('/api/hot/nrs?ids=TSMC')
    assert other.headers.get('ETag') != et
    allv = c.get('/api/hot/nrs')
    d = allv.get_json()['data']
    assert set(d) == {'values', 'n', 'unknown_ids', 'fund_version', 'method'} and d['n'] > 900
    assert allv.headers['ETag'] != et


def _metrics_client(monkeypatch, g):
    import matrix.api as M
    import server
    monkeypatch.setattr(M, '_db', lambda: (lambda: None))     # "hay base": la ruta delega en la vista
    monkeypatch.setattr(M, '_hot', lambda scope, as_of=None: g)
    return server.app.test_client()


def test_metrics_sin_top_igual_y_con_top_recortado(app, monkeypatch):
    from core.hotviews.views import impact
    _c, g = app
    c = _metrics_client(monkeypatch, g)
    ref = impact.metrics_payload(g.views['graph_core'], g.views['impact'])
    d = c.get('/api/matrix/metrics').get_json()
    assert set(d) == set(ref) | {'view'}                      # sin metrics_total/top
    assert d['metrics'] == ref['metrics'] and d['nodes'] == len(ref['metrics'])
    t = c.get('/api/matrix/metrics?top=10').get_json()
    assert t['top'] == 10 and t['metrics_total'] == len(ref['metrics']) and len(t['metrics']) == 10
    best = sorted(ref['metrics'].items(), key=lambda kv: kv[1]['chokepoint_rank'])[:10]
    assert t['metrics'] == dict(best)
    for k in ('nodes', 'factors_active', 'chokepoints_top25', 'central_pagerank_top25', 'spectral'):
        assert t[k] == d[k], k
    big = c.get('/api/matrix/metrics?top=99999').get_json()
    assert big['metrics'] == ref['metrics'] and big['metrics_total'] == len(ref['metrics'])
    for bad in ('0', 'x', '-3', '100001'):
        r = c.get(f'/api/matrix/metrics?top={bad}')
        assert r.status_code == 400 and r.get_json()['param'] == 'top' and r.get_json()['error_en']


def test_metrics_top_no_toca_lo_cacheado():
    import matrix.api as M
    payload = {'nodes': 3, 'metrics': {'a': {'chokepoint_rank': 2}, 'b': {'chokepoint_rank': 1},
                                       'c': {'chokepoint_rank': 3}}}
    out = M._metrics_top(payload, 2)
    assert list(out['metrics']) == ['b', 'a'] and out['metrics_total'] == 3
    assert len(payload['metrics']) == 3 and 'top' not in payload
    assert M._metrics_top(payload, None) is payload


DATABASE_URL = os.getenv('DATABASE_URL', '')


@pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
def test_metrics_top_por_el_camino_directo(monkeypatch):
    """Sin vista rápida (cálculo directo con caché por versión): mismo recorte, y la caché guarda el cuerpo ENTERO."""
    import matrix.api as M
    import server
    from core import http as h
    from core.hotviews import registry
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    try:
        with session_scope() as s:
            for oid in ('PG_A', 'PG_B', 'PG_C', 'PG_D'):
                apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company'}, valid_from='2000-01-01',
                            source='test', actor='pytest', object_id=oid)
            for a, b in (('PG_A', 'PG_B'), ('PG_B', 'PG_C'), ('PG_A', 'PG_D')):
                apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 4.0}, valid_from='2000-01-01',
                            source='test', actor='pytest', object_id=a, target_id=b)
        monkeypatch.setattr(M, '_hot', lambda scope, as_of=None: None)
        monkeypatch.setattr(M, '_TTL_CACHE', {})
        with h._rate_lock:
            h._rate_buckets.clear()
        c = server.app.test_client()
        full = c.get('/api/matrix/metrics').get_json()
        assert full['view']['source'] == 'direct' and 'top' not in full and len(full['metrics']) == full['nodes']
        t = c.get('/api/matrix/metrics?top=2').get_json()             # sale de la caché por versión
        assert t['view']['source'] == 'direct' and t['top'] == 2 and t['metrics_total'] == full['nodes']
        best = sorted(full['metrics'].items(), key=lambda kv: kv[1]['chokepoint_rank'])[:2]
        assert t['metrics'] == dict(best)
        again = c.get('/api/matrix/metrics').get_json()
        assert again['metrics'] == full['metrics'] and 'top' not in again   # la caché no quedó recortada
    finally:
        registry.reset()
        Base.metadata.drop_all(engine)
