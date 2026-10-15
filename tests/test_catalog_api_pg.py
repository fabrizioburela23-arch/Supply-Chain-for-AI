"""tests/test_catalog_api_pg.py — EXPANSION_5K E3.1 (lote L) con Postgres: lo que solo está en la base llega al navegador.

  · Base con el catálogo migrado (937 / 2.510): /api/hot/catalog no trae NADA (el navegador queda idéntico) y dice
    que no falta ninguna empresa ni vínculo del catálogo en la base.
  · Se importan 2 empresas con el importador (plan → aplicar, UNA decisión): salen exactamente esas dos, con sus
    campos compactos (país ISO-2, símbolo de Yahoo principal, estado), sus vínculos vivos (también hacia empresas
    del catálogo) y, a pedido, sus textos y el texto de cada vínculo; el NRS del servidor (/api/hot/nrs) las conoce en
    la MISMA generación.
  · Deshacer la corrida (ontology.import_rollback) → la diferencia vuelve a ser vacía.

Requiere DATABASE_URL (base desechable: se migra el catálogo entero, ~35 s). Sin red, sin IA.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('KHIPU_SCHEDULER', 'off')

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
F = {'source_url': 'https://www.sec.gov/Archives/edgar/data/1/x.htm', 'source_kind': 'primary', 'as_of': '2025', 'confidence': 0.9}


def _ficha(rid, hint, name, hq, rels, listing=None, status='public'):
    rec = {'schema': 'khipus.company/1', 'record_id': rid, 'khipus_id_hint': hint,
           'research_meta': {'researcher': 't', 'researched_at': '2026-10-15T00:00:00Z', 'method': 'manual', 'tier': 'B',
                             'batch': 'catalog-api'},
           'identity': {'legal_name': {'value': f'{name} Corporation', **F}, 'short_name': name,
                        'status': {'value': status, **F}, 'hq_country': {'value': hq, **F}},
           'classification': {'cat': 'memory'},
           'profile': {'summary': {'value': f'{name}: fabricante de prueba para el mapa', 'value_en': f'{name}: test maker for the map', **F}},
           'relations': rels}
    if listing:
        rec['listings'] = [listing]
    return rec


def _rel(rid, other, rel_type, role, label):
    return {'relation_id': rid, 'counterparty': {'name': other, 'khipus_id': other}, 'rel_type': rel_type, 'this_role': role,
            'label_es': label, 'label_en': label + ' (en)', 'status': 'active', 'dependency': {'criticality': 3},
            'evidence': [{'source_url': f'https://www.sec.gov/{rid}', 'as_of': '2025', 'source_kind': 'primary', 'quote': 'q'}],
            'confidence': 0.8}


@pytest.fixture(scope='module')
def db():
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    import brokerage.models  # noqa: F401
    import mcp_server.models  # noqa: F401
    import research.models  # noqa: F401
    from ontology import import_models
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    import_models._reset_for_tests()
    assert init_schema(retries=1)
    from scripts.migrate_v0_to_ontology import run_migration
    assert run_migration(reset=False, log=lambda *_a: None)
    assert import_models.ensure_tables(engine)
    yield engine
    Base.metadata.drop_all(engine)


def _rebuild():
    from core.hotviews import builder, hot, registry
    registry.reset()
    hot.invalidate()
    g = builder.build_once()
    assert g.source == 'pg'
    return hot.graph()


def _client():
    from flask import Flask

    from core.hotviews.api import hot_bp
    app = Flask('t_catalog_pg')
    app.register_blueprint(hot_bp)
    return app.test_client()


def _rows(fields, rows):
    return [dict(zip(fields, r)) for r in rows]


@pytest.fixture(scope='module')
def ronda(db):
    from core import identity
    from ontology import company_import as CI
    from ontology.db import session_scope
    v0 = _rebuild()
    c = _client()
    before = c.get('/api/hot/catalog').get_json()['data']
    recs = [_ficha('cat-api-1', 'MapaCellsKR', 'Mapa Cells', 'KR',
                   [_rel('r1', 'TSMC', 'supply', 'supplier', 'Celdas de prueba para TSMC'),
                    _rel('r2', 'Nvidia', 'partner', 'partner', 'Socio de prueba con Nvidia')],
                   listing={'ticker': '000002', 'exchange_mic': 'XKRX', 'yahoo_symbol': '000002.KS', 'currency': 'KRW',
                            'kind': 'equity', 'is_primary': True, 'source_url': 'https://ex.com/l', 'as_of': '2026'}),
            _ficha('cat-api-2', 'MapaFabJP', 'Mapa Fab', 'JP',
                   [_rel('r3', 'MapaCellsKR', 'supply', 'customer', 'Compra celdas a Mapa Cells')], status='private')]
    p = CI.plan(recs, [], view=v0, batch='catalog-api')
    assert p['counts']['create'] == 2, p['counts']
    principal = identity.operator('ui', 'pytest')
    res = CI.apply_run(session_scope, p, principal, confirm_db=None, expect={'plan_sha': p['plan_sha']}, view=v0)
    v1 = _rebuild()
    after = c.get('/api/hot/catalog').get_json()['data']
    detail = c.get('/api/hot/catalog/detail?ids=MapaCellsKR,MapaFabJP,TSMC').get_json()['data']
    nrs = c.get('/api/hot/nrs?ids=MapaCellsKR,MapaFabJP').get_json()
    with session_scope() as s:
        rb = CI.rollback_run(s, res['run_id'], principal, confirm_db=None)
    _rebuild()
    back = c.get('/api/hot/catalog').get_json()['data']
    return {'before': before, 'after': after, 'detail': detail, 'nrs': nrs, 'back': back, 'res': res, 'rb': rb,
            'v1_gen': v1.generation}


def test_catalogo_migrado_la_diferencia_es_vacia(ronda):
    d = ronda['before']
    assert d['source'] == 'pg' and d['fallback'] is False
    assert d['nodes'] == [] and d['links'] == [] and d['aliases'] == {}
    assert d['stats']['catalog_nodes_missing_in_db'] == 0 and d['stats']['catalog_links_missing_in_db'] == 0


def test_las_importadas_llegan_al_navegador(ronda):
    d = ronda['after']
    assert d['generation'] == ronda['v1_gen'] and d['total_nodes'] == 2
    nodes = {o['id']: o for o in _rows(d['node_fields'], d['nodes'])}
    assert set(nodes) == {'MapaCellsKR', 'MapaFabJP'}
    a, b = nodes['MapaCellsKR'], nodes['MapaFabJP']
    assert (a['label'], a['cat'], a['country_iso2'], a['mkt'], a['status']) == ('Mapa Cells', 'memory', 'KR', '000002.KS', 'public')
    assert a['ticker'].startswith('000002 · ') and a['country']
    assert (b['country_iso2'], b['mkt'], b['status'], b['ticker']) == ('JP', None, 'private', '')
    links = {(l['source'], l['target'], l['type']) for l in _rows(d['link_fields'], d['links'])}
    assert ('MapaCellsKR', 'TSMC', 'supply') in links and ('MapaCellsKR', 'MapaFabJP', 'supply') in links
    assert any(k[2] == 'partner' and 'Nvidia' in k[:2] and 'MapaCellsKR' in k[:2] for k in links)
    assert d['names'].get('Mapa Cells Corporation') is None     # empieza con la etiqueta: la búsqueda ya la encuentra


def test_detalle_y_mismo_nrs_que_el_servidor(ronda):
    x = ronda['detail']['nodes']
    assert x['MapaCellsKR']['role'].startswith('Mapa Cells: fabricante') and x['MapaCellsKR']['role_en'].startswith('Mapa Cells: test')
    assert x['MapaCellsKR']['listing']['yahoo_symbol'] == '000002.KS'
    assert ronda['detail']['catalog_ids'] == ['TSMC']
    rels = {tuple(r[:3]): r[3] for r in ronda['detail']['rels']}
    assert rels[('MapaCellsKR', 'TSMC', 'supply')] == 'Celdas de prueba para TSMC'
    vals = ronda['nrs']['data']['values']
    assert set(vals) == {'MapaCellsKR', 'MapaFabJP'} and all(0 <= v <= 100 for v in vals.values())
    assert ronda['nrs']['view']['generation'] == ronda['v1_gen']


def test_deshacer_vacia_la_diferencia(ronda):
    assert ronda['rb']['run_id'] == ronda['res']['run_id'] and ronda['rb']['events_reverted'] > 0 and ronda['rb']['decision_id']
    d = ronda['back']
    assert d['nodes'] == [] and d['links'] == []
