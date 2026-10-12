"""tests/test_hot_contract.py — INFRA_OPERATIVA paso 4 (§4.1, §4.6): el contrato de /api/hot/* y de las
rutas /api/matrix/* que delegan.

Toda respuesta trae el sobre `view` {generation, graph_version, release, built_at, source, stale, …} y la
cabecera X-Khipu-Graph-Version; las GET de /api/hot/* traen ETag y responden 304; errores bilingües; límite
de tasa; nada bajo /v1/*. Sin base: las vistas salen del snapshot (la app no depende de Postgres).
"""
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
VIEW_KEYS = {'generation', 'graph_version', 'release', 'built_at', 'source', 'stale', 'lag_versions', 'age_ms'}


@pytest.fixture
def snapshot_app(monkeypatch):
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


def _check(r, name=None):
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert set(d) >= {'data', 'view'}
    assert VIEW_KEYS <= set(d['view']), d['view']
    if name:
        assert d['view']['name'] == name
    assert r.headers.get('X-Khipu-Graph-Version') == str(d['view']['graph_version'])
    return d


def test_status_impact_chokepoints_factors_scenario_traen_el_sobre(snapshot_app):
    c = snapshot_app
    d = _check(c.get('/api/hot/status'), 'status')
    assert d['data']['source'] == 'snapshot' and d['data']['views']['impact']['sources'] > 900
    d = _check(c.get('/api/hot/impact/TSMC?top=5'), 'impact')
    assert d['view']['source'] == 'snapshot' and d['data']['precomputed'] is True
    assert len(d['data']['victims']) == 5 and d['data']['reach_1'] > 200
    assert all({'id', 'label', 'pct', 'hop'} <= set(v) for v in d['data']['victims'])
    d = _check(c.get('/api/hot/impact/TSMC?severity=50&kind=shock'), 'impact')
    assert d['data']['precomputed'] is False and d['data']['reach_1'] < 300
    d = _check(c.get('/api/hot/chokepoints?by=count&limit=3'), 'impact')
    assert [x['rank'] for x in d['data']['chokepoints']] == [1, 2, 3]
    d = _check(c.get('/api/hot/factors'), 'graph_core')
    assert d['data']['count'] > 50 and 'members_fragility' in d['data']['factors'][0]
    d = _check(c.post('/api/hot/scenario', json={'shocks': [{'id': 'TSMC', 'magnitude': 1},
                                                            {'id': 'NoExiste', 'magnitude': 1}]}), 'impact')
    assert d['data']['unknown_ids'] == ['NoExiste'] and d['data']['reach_1'] > 200 and 'impacts' not in d['data']


def test_mismo_numero_en_impact_y_en_scenario(snapshot_app):
    c = snapshot_app
    a = c.get('/api/hot/impact/TSMC').get_json()['data']
    b = c.post('/api/hot/scenario', json={'shocks': ['TSMC'], 'full': True}).get_json()['data']
    assert a['reach_1'] == b['reach_1'] and a['sum_impact'] == b['sum_impact'] and a['by_hop'] == b['by_hop']


def test_etag_y_304(snapshot_app):
    c = snapshot_app
    r = c.get('/api/hot/impact/TSMC')
    tag = r.headers.get('ETag')
    assert tag and tag.startswith('"impact:g0.r') and tag.endswith('.snapshot"')
    r2 = c.get('/api/hot/impact/TSMC', headers={'If-None-Match': tag})
    assert r2.status_code == 304


def test_errores_bilingues(snapshot_app):
    c = snapshot_app
    r = c.get('/api/hot/impact/NoExiste123')
    assert r.status_code == 404 and r.get_json()['error_en'] and r.get_json()['code'] == 'unknown_id'
    for url in ('/api/hot/impact/TSMC?kind=boom', '/api/hot/impact/TSMC?severity=abc',
                '/api/hot/chokepoints?by=raro'):
        r = c.get(url)
        assert r.status_code == 400 and r.get_json()['error'] and r.get_json()['error_en'], url
    r = c.post('/api/hot/scenario', json={'shocks': ['TSMC'], 'direction': 'up'})
    assert r.status_code == 400 and 'paso 12' in r.get_json()['error'] and r.get_json()['error_en']
    r = c.post('/api/hot/scenario', json={'shocks': []})
    assert r.status_code == 400 and r.get_json()['error_en']


def test_sin_generacion_responde_view_warming(monkeypatch, snapshot_app):
    from core.hotviews import builder
    monkeypatch.setattr(builder, 'current', lambda timeout=2.0: None)
    r = snapshot_app.get('/api/hot/impact/TSMC')
    assert r.status_code == 503 and r.get_json()['code'] == 'view_warming' and r.get_json()['error_en']
    assert r.headers.get('Retry-After') == '3'


@pytest.mark.parametrize('method,url,fname', [
    ('get', '/api/hot/impact/TSMC', 'hot_impact'),
    ('get', '/api/hot/chokepoints', 'hot_chokepoints'),
    ('get', '/api/hot/factors', 'hot_factors'),
    ('get', '/api/hot/status', 'hot_status'),
    ('post', '/api/hot/scenario', 'hot_scenario'),
])
def test_rutas_hot_tienen_limite_de_tasa(snapshot_app, method, url, fname):
    from core import http as h
    with h._rate_lock:
        h._rate_buckets[f'127.0.0.1:{fname}'] = [time.time()] * 500
    r = getattr(snapshot_app, method)(url, json={})
    assert r.status_code == 429 and r.get_json()['code'] == 'rate_limited'


def test_nada_bajo_v1():
    import server
    rules = [r.rule for r in server.app.url_map.iter_rules() if 'hot' in r.endpoint]
    assert rules and all(r.startswith('/api/hot/') for r in rules)


# ── rutas que delegan (con Postgres) ─────────────────────────────────────────
@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from core.hotviews import registry
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    with session_scope() as s:
        for oid in ('HC_A', 'HC_B', 'HC_C'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=oid)
        for a, b in (('HC_A', 'HC_B'), ('HC_B', 'HC_C')):
            apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 6.0}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=a, target_id=b)
        apply_event(s, 'ObjectCreated', {'label': 'FX', 'type': 'Factor',
                                         'properties': {'severity': 1.0, 'severity_crisis': 8.0}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='HC_FX')
        apply_event(s, 'LinkCreated', {'rel_type': 'affects', 'weight': 0.5}, valid_from='2000-01-01',
                    source='test', actor='pytest', object_id='HC_FX', target_id='HC_B')
    registry.reset()
    yield engine
    registry.reset()
    Base.metadata.drop_all(engine)


@needs_db
def test_rutas_matrix_delegadas_traen_el_sobre_y_la_cabecera(db):
    import server
    from core import http as h
    with h._rate_lock:
        h._rate_buckets.clear()
    c = server.app.test_client()
    for method, url, body in (('get', '/api/matrix/status', None), ('post', '/api/matrix/impact', {'shock': ['HC_A']}),
                              ('get', '/api/matrix/metrics', None), ('get', '/api/matrix/factors', None),
                              ('post', '/api/matrix/factor/fire', {'factor_id': 'HC_FX'})):
        r = getattr(c, method)(url, json=body) if body is not None else getattr(c, method)(url)
        assert r.status_code == 200, (url, r.get_json())
        d = r.get_json()
        assert VIEW_KEYS <= set(d['view']) and d['view']['source'] == 'pg' and d['view']['stale'] is False, url
        assert r.headers.get('X-Khipu-Graph-Version') == str(d['view']['graph_version']), url
    # mismo número en /api/hot/impact (vista) y /api/matrix/impact (delegada)
    hot = c.get('/api/hot/impact/HC_A').get_json()
    mat = c.post('/api/matrix/impact', json={'shock': ['HC_A']}).get_json()
    assert hot['view']['generation'] == mat['view']['generation']
    assert hot['data']['affected'] == mat['affected'] and hot['data']['reach_1'] == mat['affected']
    assert {v['id']: v['pct'] for v in hot['data']['victims']} == {k: p for k, p in mat['impacts'].items()
                                                                   if k != 'HC_A'}
    # el contrato de antes sigue (claves de siempre)
    st = c.get('/api/matrix/status').get_json()
    assert {'available', 'objects', 'rel_types', 'active_factors'} <= set(st)
    # as_of: fuera de las vistas, contrato de siempre (sin sobre)
    r = c.post('/api/matrix/impact', json={'shock': ['HC_A'], 'as_of': '2024-01-03'})
    assert r.status_code == 200 and 'view' not in r.get_json()


@needs_db
def test_cualquier_respuesta_api_lleva_la_version_conocida(db):
    import server
    from core.hotviews import signals
    c = server.app.test_client()
    r = c.get('/api/health')
    v = signals.known().get('v')
    if v:
        assert r.headers.get('X-Khipu-Graph-Version') == str(v)
