"""tests/test_catalog_api.py — EXPANSION_5K E3.1 (lote L): GET /api/hot/catalog y /api/hot/catalog/detail, sin base.

La ruta da la DIFERENCIA entre el grafo de los lectores (hot.graph()) y el catálogo estático que el navegador ya trae
(data/grafo_v0.json = nodes/*.js): solo lo que falta, en columnas compactas, paginado, con ETag = generación.

  · Sin base (generación del snapshot) la diferencia es VACÍA: con 937 empresas el navegador queda idéntico.
  · Con un grafo de lectores que trae empresas y vínculos de más (armado a mano sobre el snapshot real): salen
    exactamente esos; un id que el catálogo ya usa como alias nunca sale como 2.º nodo; un vínculo que el catálogo ya
    tiene (misma clave origen→destino·tipo) no se repite; un vínculo nuevo ENTRE empresas del catálogo sí sale.
  · conf/verified efectivos como el kernel (texto «no verificado» → 0,3 / false); señal 🔴/🟡 del NRS sin el texto;
    valuación VERIFICADA solo en USD, con fuente y confianza ≥ policy.import.live_min_confidence; nombres para la
    búsqueda del navegador solo si son buscables allí (latinos, ≥ 4 caracteres) y de UNA sola empresa.
  · Paginación (nodos primero, vínculos después), 409 si la generación cambió entre páginas, 304 con el ETag,
    400 bilingüe con parámetros inválidos; el detalle trae textos de empresas nuevas y el texto de vínculos nuevos.
"""
import copy
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('KHIPU_SCHEDULER', 'off')


def _app():
    from flask import Flask

    from core.hotviews.api import hot_bp
    app = Flask('t_catalog')
    app.register_blueprint(hot_bp)
    return app.test_client()


def _view_from(g):
    """GraphView de lectores (con su Generation) armada desde un dict con la forma del snapshot — el MISMO código que
    usan las vistas (source.from_snapshot → graph_core/impact/graph)."""
    from core.hotviews import registry, signals, source
    from core.hotviews.views import graph as graph_view
    from core.hotviews.views import graph_core, impact
    data = source.from_snapshot(g, sha='t' * 64)
    core = graph_core.build(data)
    imp = impact.build(core)
    gv = graph_view.build(data)
    rel, label = signals.release_hash()
    gen = registry.make(data, {'graph_core': core, 'impact': imp, 'graph': gv}, rel, label, {'total': 0.0},
                        {'graph_core': core.content_sha, 'impact': imp.content_sha})
    gv.attach(gen)
    return gv


@pytest.fixture(scope='module')
def snap():
    from core.hotviews import source
    g, _sha = source._snapshot_parsed()
    return g


@pytest.fixture(scope='module')
def extra(snap):
    """El snapshot real + lo que solo tendría la base."""
    g = copy.deepcopy(snap)
    keys = {(l['source'], l['target'], l.get('type') or 'supply') for l in g['links']}
    ids = [n['id'] for n in g['nodes']]
    pair = next((a, b) for a in ('Nvidia', 'ASML', 'Apple') for b in ids          # nunca TSMC (lo usa el detalle)
                if a != b and b != 'TSMC' and (a, b, 'license') not in keys and (b, a, 'license') not in keys)
    alias_key = sorted((g.get('node_id_alias') or {}).keys())[0]
    exist = g['links'][0]
    F = {'source_url': 'https://www.sec.gov/x', 'as_of': '2026'}
    g['nodes'] += [
        {'id': 'ZzTestNew1', 'label': 'Zeta Uno', 'cat': 'memory', 'sector': 'semis', 'country': 'Corea',
         'country_iso2': 'KR', 'ticker': '0001 · Corea (KRX)', 'mkt': '0001.KS', 'status': 'public', 'margin': 0.31,
         'growth': '🔴 caen las ventas', 'legal_name': 'Zeta Uno Holdings Co., Ltd.',
         'aliases': ['ZUNO Memory', 'LG화학', 'Z1', 'Shared Name Corp'], 'role': 'Memorias de prueba', 'role_en': 'Test memory',
         'hq_city': 'Seúl', 'founded': '1999', 'employees': 1200,
         'listing': {'symbol': '0001', 'mic': 'XKRX', 'yahoo_symbol': '0001.KS', 'currency': 'KRW', 'kind': 'equity'}},
        {'id': 'ZzTestNew2', 'label': 'Zeta Dos', 'cat': 'memory', 'country': 'EEUU', 'country_iso2': 'US',
         'status': 'private', 'preipo': True, 'mkt': 'ZDOS', 'growth': '🟡 estable',
         'aliases': ['Shared Name Corp'],
         'valuation': {**F, 'value': 2.5e9, 'currency': 'USD', 'as_of': '2026-01', 'round': 'Serie B', 'confidence': 0.8}},
        {'id': 'ZzTestNew3', 'label': 'Zeta Tres', 'cat': 'memory', 'status': 'private',
         'valuation': {**F, 'value': 9e9, 'currency': 'EUR', 'as_of': '2026-01', 'confidence': 0.9}},
        {'id': 'ZzTestNew4', 'label': 'Zeta Cuatro', 'cat': 'memory', 'status': 'private',
         'valuation': {**F, 'value': 3e9, 'currency': 'USD', 'as_of': '2026-01', 'confidence': 0.2}},
        {'id': alias_key, 'label': 'Alias del catálogo', 'cat': 'memory'},
    ]
    g['links'] += [
        {'source': 'TSMC', 'target': 'ZzTestNew1', 'w': 4, 'rel': 'Obleas, no verificado', 'type': 'supply'},
        {'source': 'ZzTestNew1', 'target': 'ZzTestNew2', 'w': 1, 'rel': 'Socio en I+D', 'type': 'partner',
         'conf': 0.9, 'verified': True, 'since': '2024-05'},
        {'source': pair[0], 'target': pair[1], 'w': 2, 'rel': 'Licencia nueva', 'type': 'license', 'conf': 1, 'verified': True},
        dict(exist, w=6, rel='la misma clave que el catálogo'),
    ]
    g.setdefault('node_id_alias', {})['ZzOldName'] = 'ZzTestNew1'
    return {'g': g, 'pair': pair, 'alias_key': alias_key, 'exist': exist}


@pytest.fixture
def served(extra, monkeypatch):
    from core.hotviews import hot
    gv = _view_from(extra['g'])
    monkeypatch.setattr(hot, 'graph', lambda wait=True, timeout=None: gv)
    hot.invalidate()
    yield gv
    hot.invalidate()


def _rows(fields, rows):
    return [dict(zip(fields, r)) for r in rows]


def test_static_catalog_es_el_del_navegador(snap):
    from core.hotviews import api
    sha, ids, alias, lkeys = api._static_catalog()
    assert len(ids) == len({n['id'] for n in snap['nodes']}) >= 937
    assert len(lkeys) == len(snap['links'])
    assert set(alias) == set(snap.get('node_id_alias') or {})
    assert api._static_catalog() is api._static_catalog()        # una vez por versión del archivo


def test_sin_base_la_diferencia_es_vacia(monkeypatch):
    """Generación del snapshot (sin DATABASE_URL): el navegador queda IDÉNTICO (937 / 2.510)."""
    import ontology.db as odb
    from core.hotviews import builder, hot, registry
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    registry.reset()
    builder._ST.update(consecutive_failures=0, retry_at=0.0)
    hot.reset()
    try:
        c = _app()
        r = c.get('/api/hot/catalog')
        assert r.status_code == 200, r.get_data(as_text=True)[:300]
        d = r.get_json()['data']
        assert d['nodes'] == [] and d['links'] == [] and d['aliases'] == {} and d['names'] == {}
        assert d['total_nodes'] == 0 and d['total_links'] == 0 and d['next_offset'] is None
        assert d['base']['catalog_nodes'] >= 937 and d['base']['catalog_links'] >= 2510
        assert d['node_fields'][:3] == ['id', 'label', 'cat'] and 'gflag' in d['node_fields']
        assert r.headers['ETag'].startswith('"catalog:') and r.headers['Cache-Control'] == 'no-cache'
        assert r.headers.get('X-Khipu-Graph-Version') is not None
        r2 = c.get('/api/hot/catalog', headers={'If-None-Match': r.headers['ETag']})
        assert r2.status_code == 304
    finally:
        registry.reset()
        hot.reset()


def test_solo_lo_que_falta(served, extra):
    c = _app()
    d = c.get('/api/hot/catalog').get_json()['data']
    nodes = {o['id']: o for o in _rows(d['node_fields'], d['nodes'])}
    assert set(nodes) == {'ZzTestNew1', 'ZzTestNew2', 'ZzTestNew3', 'ZzTestNew4'}
    assert extra['alias_key'] not in nodes                     # el navegador ya lleva ese id a un nodo: nunca 2.º nodo
    assert d['stats']['skipped_alias_n'] == 1 and d['stats']['skipped_alias_ids'] == [extra['alias_key']]
    n1, n2 = nodes['ZzTestNew1'], nodes['ZzTestNew2']
    assert (n1['label'], n1['cat'], n1['country'], n1['country_iso2']) == ('Zeta Uno', 'memory', 'Corea', 'KR')
    assert (n1['ticker'], n1['mkt'], n1['status'], n1['preipo'], n1['margin']) == ('0001 · Corea (KRX)', '0001.KS', 'public', 0, 0.31)
    assert n1['gflag'] == 'r' and n2['gflag'] == 'y' and nodes['ZzTestNew3']['gflag'] is None
    assert n2['preipo'] == 1 and n2['mkt'] is None and n2['ticker'] == ''      # una privada no «cotiza» por su relleno
    assert 'role' not in d['node_fields']                      # los textos van a pedido (detalle)
    links = {(l['source'], l['target'], l['type']): l for l in _rows(d['link_fields'], d['links'])}
    p = extra['pair']
    assert set(links) == {('TSMC', 'ZzTestNew1', 'supply'), ('ZzTestNew1', 'ZzTestNew2', 'partner'), (p[0], p[1], 'license')}
    e = extra['exist']
    assert (e['source'], e['target'], e.get('type') or 'supply') not in links   # misma clave que el catálogo: no se repite
    t = links[('TSMC', 'ZzTestNew1', 'supply')]
    assert (t['w'], t['conf'], t['verified']) == (4, 0.3, False)              # «no verificado» → 0,3 como el kernel
    s = links[('ZzTestNew1', 'ZzTestNew2', 'partner')]
    assert (s['conf'], s['verified'], s['since']) == (0.9, True, '2024-05')
    assert d['stats']['flow_links'] == 2 and d['stats']['nonflow_links'] == 1
    assert sorted(d['flow_types']) == sorted(['cloud', 'deploy', 'fab', 'license', 'owns', 'ppa', 'supply'])
    assert d['aliases'] == {'ZzOldName': 'ZzTestNew1'}


def test_valuacion_verificada_y_nombres(served):
    d = _app().get('/api/hot/catalog').get_json()['data']
    assert set(d['valuations']) == {'ZzTestNew2'}             # EUR (sin conversión) y confianza 0,2 no dimensionan
    v = d['valuations']['ZzTestNew2']
    assert (v['usd_b'], v['as_of'], v['round'], v['source_url']) == (2.5, '2026-01', 'Serie B', 'https://www.sec.gov/x')
    # «Zeta Uno Holdings…» empieza con la etiqueta (la búsqueda ya la encuentra); «LG화학» y «Z1» no son buscables en
    # el navegador; «Shared Name Corp» lo reclaman dos empresas → no resuelve a ninguna
    assert d['names'] == {'ZUNO Memory': 'ZzTestNew1'}


def test_paginas_generacion_y_parametros(served):
    c = _app()
    full = c.get('/api/hot/catalog').get_json()['data']
    assert full['next_offset'] is None and full['limit'] == 5000
    p1 = c.get('/api/hot/catalog?limit=3').get_json()['data']
    assert (len(p1['nodes']), len(p1['links']), p1['next_offset']) == (3, 0, 3)
    gen = p1['generation']
    p2 = c.get(f'/api/hot/catalog?limit=3&offset=3&gen={gen}').get_json()['data']
    assert (len(p2['nodes']), len(p2['links']), p2['next_offset']) == (1, 2, 6)
    assert p2['aliases'] == {}                                 # solo en la primera página
    p3 = c.get(f'/api/hot/catalog?limit=3&offset=6&gen={gen}').get_json()['data']
    assert (len(p3['nodes']), len(p3['links']), p3['next_offset']) == (0, 1, None)
    assert p1['nodes'] + p2['nodes'] == full['nodes'] and p2['links'] + p3['links'] == full['links']
    assert set(p1['names'].values()) <= {r[0] for r in p1['nodes']}
    r = c.get('/api/hot/catalog?gen=otra')
    assert r.status_code == 409 and r.get_json()['code'] == 'generation_changed'
    assert r.get_json()['generation'] == gen and 'error_en' in r.get_json()
    for q in ('limit=0', 'limit=abc', 'offset=-1', 'limit=999999'):
        r = c.get('/api/hot/catalog?' + q)
        assert r.status_code == 400 and r.get_json()['error'] and r.get_json()['error_en'], q
    r1 = c.get('/api/hot/catalog?limit=3')
    assert c.get('/api/hot/catalog?limit=3', headers={'If-None-Match': r1.headers['ETag']}).status_code == 304
    assert r1.headers['ETag'] != c.get('/api/hot/catalog?limit=4').headers['ETag']


def test_diferencia_una_vez_por_generacion(served):
    from core.hotviews import api, hot
    _app().get('/api/hot/catalog')
    st = api._static_catalog()
    a = hot.cached(f'hot.catalog_delta:{st[0][:16]}', lambda v: pytest.fail('se recalculó'), view=served)
    assert a['delta_ids'] == frozenset({'ZzTestNew1', 'ZzTestNew2', 'ZzTestNew3', 'ZzTestNew4'})


def test_detalle_a_pedido(served):
    c = _app()
    r = c.get('/api/hot/catalog/detail?ids=ZzTestNew1,TSMC,Nope,ZzOldName')
    assert r.status_code == 200
    d = r.get_json()['data']
    assert set(d['nodes']) == {'ZzTestNew1'}                  # textos SOLO de empresas nuevas (alias → canónico)
    x = d['nodes']['ZzTestNew1']
    assert (x['role'], x['role_en'], x['hq_city'], x['founded'], x['employees']) == ('Memorias de prueba', 'Test memory', 'Seúl', '1999', 1200)
    assert x['legal_name'] == 'Zeta Uno Holdings Co., Ltd.' and x['listing']['yahoo_symbol'] == '0001.KS'
    assert d['catalog_ids'] == ['TSMC'] and d['unknown_ids'] == ['Nope']
    rels = {tuple(r[:3]): r[3] for r in d['rels']}
    assert rels[('TSMC', 'ZzTestNew1', 'supply')] == 'Obleas, no verificado'
    assert rels[('ZzTestNew1', 'ZzTestNew2', 'partner')] == 'Socio en I+D'
    assert all(k[0] != k[1] for k in rels)
    # un id del catálogo tocado por un vínculo nuevo trae el texto de ese vínculo (sin textos de la empresa)
    d2 = c.get('/api/hot/catalog/detail?ids=TSMC').get_json()['data']
    assert d2['nodes'] == {} and [tuple(r[:3]) for r in d2['rels']] == [('TSMC', 'ZzTestNew1', 'supply')]
    r = c.get('/api/hot/catalog/detail')
    assert r.status_code == 400 and r.get_json()['error_en']
    many = ','.join(f'X{i}' for i in range(300))
    assert len(c.get('/api/hot/catalog/detail?ids=' + many).get_json()['data']['unknown_ids']) == 100


def test_nombres_buscables():
    from core.hotviews.api import _searchable
    assert _searchable('LG Chem, Ltd.') and _searchable('Ørsted A/S') and _searchable('Société Générale')
    assert not _searchable('LG화학') and not _searchable('(주)엘지화학') and not _searchable('宁德时代')
    assert not _searchable('IBM') and not _searchable('') and not _searchable(None)
