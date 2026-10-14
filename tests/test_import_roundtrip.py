"""tests/test_import_roundtrip.py — EXPANSION_5K E2.3/E2.4/E2.8 con Postgres: plan → aplicar → deshacer sobre una muestra
real de 50 fichas del lote 1 + una ficha sintética con vínculos (fechado 2021-07, sin fecha → GENESIS, rumor →
propuesta, contraparte desconocida → pendiente, terminado → valid_to).

Garantiza: eventos SOLO se añaden (append-only), UNA decisión ontology.bulk_import por corrida, UNA generación del
grafo (graph_version +1), el vínculo de 2021-07 se ve en /api/ontology/graph?as_of= desde 2021-07 y no antes, el
vínculo sin start dice valid_from_known false, el deshacer devuelve el grafo de lectura y la vista Impact a su
contenido (paridad) con decisión ontology.import_rollback, 409 si el grafo cambió (plan_sha / generación), 503 sin
libro (nada se escribe), subida en trozos por la API con PIN, tablas del importador append-only.

Requiere DATABASE_URL (base desechable: se migra el catálogo entero, ~30 s). Sin red, sin IA.
"""
import base64
import hashlib
import json
import os
import sys
import zlib

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('KHIPU_SCHEDULER', 'off')

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PIN = '4321'
F = {'source_url': 'https://www.sec.gov/Archives/edgar/data/1/x.htm', 'source_kind': 'primary', 'as_of': '2025', 'confidence': 0.9}


def _synth(rid='t-synth-1', hint='SmokeCells', name='Smoke Cells'):
    return {
        'schema': 'khipus.company/1', 'record_id': rid, 'khipus_id_hint': hint,
        'research_meta': {'researcher': 't', 'researched_at': '2026-10-14T00:00:00Z', 'method': 'manual', 'tier': 'B', 'batch': 'rt'},
        'identity': {'legal_name': {'value': f'{name} Ltd', **F}, 'short_name': name, 'status': {'value': 'public', **F},
                     'hq_country': {'value': 'KR', **F}, 'founded': {'value': '2010-03', **F}},
        'listings': [{'ticker': '000001', 'exchange_mic': 'XKRX', 'yahoo_symbol': '000001.KS', 'currency': 'KRW', 'kind': 'equity',
                      'is_primary': True, 'source_url': 'https://ex.com/l', 'as_of': '2026'}],
        'classification': {'cat': 'memory'},
        'profile': {'summary': {'value': 'Fabricante de celdas de prueba para la ronda', 'value_en': 'Test cell maker for the round trip', **F}},
        'relations': [
            {'relation_id': 'rel-001', 'counterparty': {'name': 'TSMC', 'khipus_id': 'TSMC'}, 'rel_type': 'supply', 'this_role': 'supplier',
             'label_es': 'Celdas de prueba para TSMC', 'label_en': 'Test cells for TSMC', 'status': 'active', 'start': '2021-07',
             'dependency': {'criticality': 4, 'tier': 1, 'component': 'celda',
                            'supplier_facility': {'name': 'Planta A', 'country': 'KR', 'share_of_flow_pct': 100}},
             'evidence': [{'source_url': 'https://www.sec.gov/x1', 'as_of': '2025', 'source_kind': 'primary', 'quote': 'q'}], 'confidence': 0.8},
            {'relation_id': 'rel-002', 'counterparty': {'name': 'Nvidia', 'khipus_id': 'Nvidia'}, 'rel_type': 'supply', 'this_role': 'supplier',
             'label_es': 'Módulos sin fecha para Nvidia', 'label_en': 'Undated modules for Nvidia', 'status': 'active',
             'dependency': {'criticality': 2},
             'evidence': [{'source_url': 'https://www.sec.gov/x2', 'as_of': '2025', 'source_kind': 'press', 'quote': 'q'}], 'confidence': 0.6},
            {'relation_id': 'rel-003', 'counterparty': {'name': 'Apple', 'khipus_id': 'Apple'}, 'rel_type': 'supply', 'this_role': 'supplier',
             'label_es': 'Rumor con Apple', 'label_en': 'Rumor with Apple', 'status': 'rumored', 'dependency': {'criticality': 1},
             'evidence': [{'source_url': 'https://www.sec.gov/x3', 'as_of': '2025', 'source_kind': 'rumor', 'quote': 'q'}], 'confidence': 0.3},
            {'relation_id': 'rel-004', 'counterparty': {'name': 'Empresa Inexistente XYZ'}, 'rel_type': 'supply', 'this_role': 'customer',
             'label_es': 'Insumo de un desconocido', 'label_en': 'Input from unknown', 'status': 'active', 'dependency': {'criticality': 3},
             'evidence': [{'source_url': 'https://www.sec.gov/x4', 'as_of': '2025', 'source_kind': 'primary', 'quote': 'q'}], 'confidence': 0.9},
            {'relation_id': 'rel-005', 'counterparty': {'name': 'Samsung', 'khipus_id': 'Samsung'}, 'rel_type': 'supply', 'this_role': 'supplier',
             'label_es': 'Vínculo terminado', 'label_en': 'Ended link', 'status': 'ended', 'start': '2018', 'end': '2020-06',
             'dependency': {'criticality': 2},
             'evidence': [{'source_url': 'https://www.sec.gov/x5', 'as_of': '2025', 'source_kind': 'primary', 'quote': 'q'}], 'confidence': 0.9},
        ]}


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


@pytest.fixture(scope='module')
def bundle():
    from ontology import company_import as CI
    b = CI.adapt_lote_2026_10_14()
    return {'records': b['records'][:50] + [_synth()], 'updates': b['updates'][:20], 'batch': 'rt'}


def _counts(s):
    from sqlalchemy import text
    return {'events': s.execute(text('select count(*) from events')).scalar(),
            'decisions': {r[0]: r[1] for r in s.execute(text('select kind, count(*) from decisions group by kind'))},
            'links': s.execute(text('select count(*) from links where valid_to is null')).scalar()}


def _principal():
    from core import identity
    return identity.operator('ui', 'pytest')


@pytest.fixture(scope='module')
def ronda(db, bundle):
    """plan → aplicar → (comprobaciones) → deshacer, con las fotos intermedias para las pruebas."""
    from ontology import company_import as CI
    from ontology.db import session_scope
    from ontology.service import as_of_graph
    v0 = _rebuild()
    core0, imp0 = v0.core.content_sha, v0.impact.content_sha
    nodes0, links0 = {n['id'] for n in v0.nodes}, {(l['source'], l['target'], l['type']) for l in v0.links}
    with session_scope() as s:
        c0 = _counts(s)
    p = CI.plan(bundle['records'], bundle['updates'], view=v0, batch=bundle['batch'])
    res = CI.apply_run(session_scope, p, _principal(), confirm_db=None, expect={'plan_sha': p['plan_sha']}, view=v0)
    with session_scope() as s:
        c1 = _counts(s)
        asof = {d: [(l['source'], l['target'], l.get('valid_from_known'), (l.get('properties') or {}).get('status'))
                    for l in as_of_graph(s, d)['links'] if 'SmokeCells' in (l['source'], l['target'])]
                for d in ('2019-01-01', '2021-06-01', '2021-08-01', '2026-10-14')}
        pend = CI.pending_links(s)
        runs1 = CI.list_runs(s)
    v1 = _rebuild()
    out = {'v0': {'gen': v0.generation, 'gv': v0.graph_version, 'core': core0, 'impact': imp0, 'nodes': nodes0, 'links': links0,
                  'tsmc': v0.impact.stats['TSMC']['reach_1']},
           'plan': p, 'res': res, 'c0': c0, 'c1': c1, 'asof': asof, 'pending': pend, 'runs1': runs1,
           'v1': {'gen': v1.generation, 'gv': v1.graph_version, 'nodes': {n['id'] for n in v1.nodes},
                  'links': {(l['source'], l['target'], l['type']) for l in v1.links}, 'tsmc': v1.impact.stats['TSMC']['reach_1'],
                  'smoke': dict(v1.by_id.get('SmokeCells') or {})}}
    with session_scope() as s:
        rb = CI.rollback_run(s, res['run_id'], _principal(), confirm_db=None)
    with session_scope() as s:
        c2 = _counts(s)
        runs2 = CI.list_runs(s)
    v2 = _rebuild()
    out.update(rb=rb, c2=c2, runs2=runs2,
               v2={'gen': v2.generation, 'gv': v2.graph_version, 'core': v2.core.content_sha, 'impact': v2.impact.content_sha,
                   'nodes': {n['id'] for n in v2.nodes}, 'links': {(l['source'], l['target'], l['type']) for l in v2.links},
                   'tsmc': v2.impact.stats['TSMC']['reach_1']})
    return out


def test_plan_sobre_postgres(ronda):
    p = ronda['plan']
    assert p['graph_source'] == 'pg' and p['counts']['valid'] == 51 and p['counts']['invalid'] == 0
    it = next(i for i in p['items'] if i['record_id'] == 't-synth-1')
    assert it['action'] == 'create' and it['id'] == 'SmokeCells'
    routes = {l['relation_id']: (l['route'], l['reason']) for l in it['links']}
    assert routes == {'rel-001': ('live', 'ok'), 'rel-002': ('live', 'ok'), 'rel-003': ('proposed', 'status_rumored'),
                      'rel-004': ('pending', 'counterparty_unknown'), 'rel-005': ('live', 'ok')}
    l1 = next(l for l in it['links'] if l['relation_id'] == 'rel-001')
    assert l1['source'] == 'SmokeCells' and l1['target'] == 'TSMC' and l1['valid_from'].startswith('2021-07-01') and l1['valid_from_known']
    assert l1['weight'] == 4.0 and l1['properties']['dependency']['supplier_facility']['name'] == 'Planta A'
    assert l1['properties']['dependency']['component'] == 'celda' and l1['properties']['dependency']['tier'] == 1
    assert l1['source_id'] and l1['properties']['verified'] is True
    l2 = next(l for l in it['links'] if l['relation_id'] == 'rel-002')
    assert l2['valid_from'] == '2000-01-01' and l2['valid_from_known'] is False
    l5 = next(l for l in it['links'] if l['relation_id'] == 'rel-005')
    assert l5['valid_to'].startswith('2020-07-01')
    wc = p['what_changes']
    assert wc['added_links'] == 3 and wc['calibration_stale'] is True and wc['before']['tsmc_hit'] == 318


def test_aplicar_una_decision_una_generacion_append_only(ronda):
    res, c0, c1 = ronda['res'], ronda['c0'], ronda['c1']
    assert res['events'] == c1['events'] - c0['events'] and res['events'] >= 100
    assert c1['decisions'].get('ontology.bulk_import', 0) - c0['decisions'].get('ontology.bulk_import', 0) == 1
    assert res['decision_id'] and res['graph_version_after'] == res['graph_version_before'] + 1
    assert ronda['v1']['gv'] == ronda['v0']['gv'] + 1
    assert res['links_created'] == 4 and res['objects_created'] >= 48 and res['pending'] == 1
    assert res['elapsed_ms'] < 30000
    assert res['gate_import'] is None or res['gate_import']['mode'] in ('shadow', 'block')


def test_fechas_reales_en_el_grafo_temporal(ronda):
    asof = ronda['asof']
    assert ('SmokeCells', 'TSMC', None, 'active') in asof['2021-08-01']      # desde 2021-07 (fecha real: known no se marca)
    assert all(t != 'TSMC' for _s, t, _k, _st in asof['2021-06-01'])           # y no antes
    nv = next(x for x in asof['2021-08-01'] if x[1] == 'Nvidia')
    assert nv[2] is False                                                      # sin start: "desde que se rastrea"
    assert any(t == 'Samsung' for _s, t, _k, _st in asof['2019-01-01'])       # 2018 → 2020-06
    assert all(t != 'Samsung' for _s, t, _k, _st in asof['2026-10-14'])       # ya terminó
    ap = next(x for x in asof['2026-10-14'] if x[1] == 'Apple')
    assert ap[3] == 'proposed'                                                 # el rumor es una PROPUESTA


def test_vista_de_lectura_tras_aplicar(ronda):
    v1 = ronda['v1']
    assert 'SmokeCells' in v1['nodes'] and v1['smoke'].get('country') == 'Corea' and v1['smoke'].get('hq_country') == 'KR'
    assert v1['smoke'].get('mkt') == '000001.KS' and v1['smoke']['texts']['role_en']
    assert ('SmokeCells', 'TSMC', 'supply') in v1['links'] and ('SmokeCells', 'Nvidia', 'supply') in v1['links']
    assert ('SmokeCells', 'Apple', 'supply') not in v1['links']              # propuesta: fuera del grafo de lectura
    assert ('SmokeCells', 'Samsung', 'supply') not in v1['links']            # terminado
    assert len(v1['nodes']) == len(ronda['v0']['nodes']) + ronda['plan']['counts']['create']
    assert ronda['pending'] and ronda['pending'][0]['counterparty']['name'] == 'Empresa Inexistente XYZ'
    assert ronda['runs1'][0]['kind'] == 'apply' and ronda['runs1'][0]['status'] == 'applied'


def test_deshacer_devuelve_el_grafo_y_deja_decision(ronda):
    rb, v0, v2, c1, c2 = ronda['rb'], ronda['v0'], ronda['v2'], ronda['c1'], ronda['c2']
    assert rb['links_retracted'] == 4 and rb['objects_retired'] == ronda['plan']['counts']['create'] and rb['decision_id']
    assert c2['events'] > c1['events']                                        # deshacer = MÁS eventos
    assert c2['decisions'].get('ontology.import_rollback', 0) - c1['decisions'].get('ontology.import_rollback', 0) == 1
    assert v2['nodes'] == v0['nodes'] and v2['links'] == v0['links']          # paridad del grafo de lectura
    assert v2['impact'] == v0['impact'] and v2['tsmc'] == v0['tsmc'] == 318   # paridad de la vista Impact
    assert c2['links'] == ronda['c0']['links']
    assert ronda['runs2'][0]['kind'] == 'rollback' and ronda['runs2'][0]['rolled_back_run']


def test_deshacer_dos_veces_y_corrida_inexistente(ronda, db):
    from ontology import company_import as CI
    from ontology.db import session_scope
    with pytest.raises(CI.ImportProblem) as e, session_scope() as s:
        CI.rollback_run(s, ronda['res']['run_id'], _principal())
    assert e.value.code == 'already_rolled_back'
    with pytest.raises(CI.ImportProblem) as e2, session_scope() as s:
        CI.rollback_run(s, 'no-existe', _principal())
    assert e2.value.code == 'run_not_found'


def test_409_si_el_plan_o_el_grafo_cambiaron(ronda, db, bundle):
    from ontology import company_import as CI
    from ontology.db import session_scope
    v = _rebuild()
    p = CI.plan([_synth('t-409', 'Cambia409', 'Cambia 409')], [], view=v, batch='409', what_changes=False)
    with pytest.raises(CI.ImportProblem) as e:
        CI.apply_run(session_scope, p, _principal(), expect={'plan_sha': '0' * 64}, view=v)
    assert e.value.code == 'plan_changed'
    # el grafo cambió desde que se armó el plan (otra escritura económica) → la generación ya no es la del plan
    from ontology.service import apply_event
    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': 'Otro', 'type': 'Company', 'properties': {}}, valid_from='2020-01-01',
                    source='pytest', actor='pytest', object_id='Otro409')
    v2 = _rebuild()
    with pytest.raises(CI.ImportProblem) as e2:
        CI.apply_run(session_scope, p, _principal(), expect={'plan_sha': p['plan_sha']}, view=v2)
    assert e2.value.code == 'graph_changed'
    with pytest.raises(CI.ImportProblem) as e3:
        CI.apply_run(session_scope, p, _principal(), expect=None, view=v)
    assert e3.value.code == 'expect_required'


def test_sin_libro_no_se_escribe_nada(ronda, db, monkeypatch):
    from sqlalchemy import text

    from core import decisions
    from ontology import company_import as CI
    from ontology.db import session_scope
    v = _rebuild()
    p = CI.plan([_synth('t-503', 'SinLibro503', 'Sin Libro 503')], [], view=v, batch='503', what_changes=False)

    def _down(*_a, **_k):
        raise decisions.LedgerUnavailable('libro caído (prueba)')
    monkeypatch.setattr(decisions, 'record', _down)
    with session_scope() as s:
        before = s.execute(text('select count(*) from events')).scalar()
    with pytest.raises(decisions.LedgerUnavailable):
        CI.apply_run(session_scope, p, _principal(), expect={'plan_sha': p['plan_sha']}, view=v)
    with session_scope() as s:
        assert s.execute(text('select count(*) from events')).scalar() == before
        assert s.get(__import__('ontology.models', fromlist=['ObjectRecord']).ObjectRecord, 'SinLibro503') is None


def test_tablas_del_importador_son_append_only(db):
    from sqlalchemy import text

    from ontology.db import session_scope
    with pytest.raises(Exception) as e, session_scope() as s:
        s.execute(text("update import_runs set status = 'x'"))
    assert 'append-only' in str(e.value)
    with pytest.raises(Exception) as e2, session_scope() as s:
        s.execute(text('delete from import_runs'))
    assert 'append-only' in str(e2.value)


# ── la API: PIN, subida en trozos, plan, aplicar (409), deshacer, corridas ─────────────────────────────────────
@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setenv('TRADE_PIN', PIN)
    import server
    from core import http as h
    from core import pin as _pin
    _pin._reset_for_tests()
    with h._rate_lock:
        h._rate_buckets.clear()
    _rebuild()
    return server.app.test_client()


H = {'X-Trade-Pin': PIN}


def _dbname():
    from sqlalchemy import text

    from ontology.db import session_scope
    with session_scope() as s:
        return s.execute(text('SELECT current_database()')).scalar()


def _upload(client, payload, chunks=2):
    raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    sha = hashlib.sha256(raw).hexdigest()
    size = max(1, (len(raw) + chunks - 1) // chunks)
    parts = [raw[i:i + size] for i in range(0, len(raw), size)]
    last = None
    for i, part in enumerate(parts):
        last = client.post('/api/ontology/import/files', json={
            'name': 'rt.json', 'sha256': sha, 'chunk': i, 'chunks': len(parts),
            'data': base64.b64encode(zlib.compress(part)).decode('ascii'), 'encoding': 'zlib', 'actor': 'pytest'}, headers=H)
        assert last.status_code == 200, last.get_data(as_text=True)[:300]
    return sha, last.get_json()


def test_api_pin_obligatorio(client):
    for url in ('/api/ontology/import/files', '/api/ontology/import/plan', '/api/ontology/import/apply',
                '/api/ontology/import/rollback'):
        r = client.post(url, json={})
        assert r.status_code in (401, 403), (url, r.status_code)      # sin PIN (401) / PIN malo (403): nunca entra


def test_api_subida_plan_aplicar_deshacer(client):
    from sqlalchemy import text

    from ontology.db import session_scope
    payload = {'schema': 'khipus.import/1', 'batch': 'api-rt', 'records': [_synth('t-api-1', 'ApiCells', 'Api Cells')],
               'updates': [], 'approve_categories': []}
    sha, up = _upload(client, payload, chunks=2)
    assert up['status'] == 'stored' and up['n_records'] == 1 and up['sha256'] == sha
    with session_scope() as s:
        assert s.execute(text('select count(*) from import_files where sha256 = :s'), {'s': sha}).scalar() == 1
    r = client.post('/api/ontology/import/plan', json={'file_sha': sha}, headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    plan = r.get_json()['plan']
    assert plan['counts']['create'] == 1 and len(plan['plan_sha']) == 64 and plan['items'][0]['action'] == 'create'
    assert 'props' not in plan['items'][0]                                   # resumen sin propiedades
    r_md = client.post('/api/ontology/import/plan', json={'file_sha': sha, 'format': 'md', 'lang': 'en'}, headers=H)
    assert r_md.status_code == 200 and b'Import plan' in r_md.data
    # huella equivocada → 409
    r = client.post('/api/ontology/import/apply', json={'file_sha': sha, 'expect': {'plan_sha': '1' * 64}, 'actor': 'pytest',
                                                         'confirm_db': _dbname()}, headers=H)
    assert r.status_code == 409 and r.get_json()['code'] == 'plan_changed'
    r = client.post('/api/ontology/import/apply', json={'file_sha': sha, 'actor': 'pytest'}, headers=H)
    assert r.status_code == 400 and r.get_json()['code'] == 'expect_required'
    # revisión lote K: confirm_db (nombre EXACTO de la base) es obligatorio, como en reconcile
    r = client.post('/api/ontology/import/apply', json={'file_sha': sha, 'expect': {'plan_sha': plan['plan_sha']}, 'actor': 'pytest'}, headers=H)
    assert r.status_code == 400 and r.get_json()['code'] == 'confirm_required'
    r = client.post('/api/ontology/import/apply', json={'file_sha': sha, 'expect': {'plan_sha': plan['plan_sha']}, 'actor': 'pytest',
                                                         'confirm_db': 'otra_base'}, headers=H)
    assert r.status_code == 400 and r.get_json()['code'] == 'confirm_db'
    r = client.post('/api/ontology/import/apply', json={'file_sha': sha, 'expect': {'plan_sha': plan['plan_sha']}, 'actor': 'pytest',
                                                         'confirm_db': _dbname()}, headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:400]
    res = r.get_json()
    assert res['status'] == 'ok' and res['decision_id'] and res['links_created'] == 4
    r = client.get('/api/ontology/import/runs')
    assert r.status_code == 200 and r.get_json()['runs'][0]['run_id'] == res['run_id'] and r.get_json()['pending_links'] >= 1
    assert r.get_json()['runs'][0]['graph_version_after'] == res['graph_version_after'] is not None   # desde kh_tx_versions
    r = client.post('/api/ontology/import/rollback', json={'run_id': res['run_id'], 'actor': 'pytest'}, headers=H)
    assert r.status_code == 400 and r.get_json()['code'] == 'confirm_required'
    r = client.post('/api/ontology/import/rollback', json={'run_id': res['run_id'], 'actor': 'pytest', 'confirm_db': _dbname()}, headers=H)
    assert r.status_code == 200 and r.get_json()['decision_id']
    r = client.post('/api/ontology/import/rollback', json={'run_id': res['run_id'], 'actor': 'pytest', 'confirm_db': _dbname()}, headers=H)
    assert r.status_code == 409
    v = _rebuild()
    assert 'ApiCells' not in v.by_id


def test_api_trozo_con_sha_falso_y_archivo_inexistente(client):
    raw = b'{"records": []}'
    r = client.post('/api/ontology/import/files', json={'name': 'x.json', 'sha256': 'a' * 64, 'chunk': 0, 'chunks': 1,
                                                          'data': base64.b64encode(zlib.compress(raw)).decode('ascii')}, headers=H)
    assert r.status_code == 400 and r.get_json()['code'] == 'sha_mismatch'
    r = client.post('/api/ontology/import/plan', json={'file_sha': 'b' * 64}, headers=H)
    assert r.status_code == 404 and r.get_json()['code'] == 'file_not_found'
    r = client.post('/api/ontology/import/plan', json={'records': 'no'}, headers=H)
    assert r.status_code == 400
