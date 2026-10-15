"""tests/test_import_panel.py — EXPANSION_5K E2.7: rutas del panel 🩺 → 📥 Importar (ontology/api.py).

  · LISTA BLANCA de paquetes del repositorio (data/import/lotes/<AAAA-MM-DD>/bundle_*.json.gz): el cliente nunca manda
    una ruta; «..», rutas absolutas, otros archivos de la carpeta y enlaces simbólicos → 404 package_not_found;
  · GET /api/ontology/import/packages y GET /import/packages/plan SIN PIN (lectura), con la MISMA huella (plan_sha) que
    POST /import/plan {package} con PIN y que company_import.plan sobre la misma vista;
  · aplicar y deshacer el paquete real del lote 2 (386 fichas completas) por la API con PIN sobre Postgres: UNA decisión
    ontology.bulk_import / ontology.import_rollback, el paquete queda «aplicado» y luego «deshecho», el grafo vuelve;
  · {package} + {file_sha} a la vez → 400 ambiguous_source; huella vieja → 409 plan_changed;
  · `sanitize: 1` (lo manda el panel para archivos SUBIDOS) repara el formato de una ficha cruda antes del plan.

Las pruebas de la lista blanca corren sin base; el resto requiere DATABASE_URL (base desechable: se migra el catálogo).
"""
import gzip
import hashlib
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('KHIPU_SCHEDULER', 'off')

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PIN = '4321'
H = {'X-Trade-Pin': PIN}
PKG = '2026-10-15/bundle_lote2_completas.json.gz'
PKG_PATH = os.path.join(ROOT, 'data', 'import', 'lotes', *PKG.split('/'))
BAD_NAMES = ['../2026-10-15/bundle_lote2_completas.json.gz', '2026-10-15/../2026-10-15/bundle_lote2_completas.json.gz',
             '/etc/passwd', PKG_PATH, '2026-10-15/sanitize_log.json', '2026-10-15/fichas_completas.jsonl.gz',
             '2026-10-15/ORIGEN.json', '2026-10-15\\bundle_lote2_completas.json.gz', 'bundle_lote2_completas.json.gz',
             '2026-10-15/bundle_lote2_completas.json.gz/..', '', ' ', '2026-10-15/bundle_lote2_completas.json.gz\x00']


def _pkg_sha():
    with gzip.open(PKG_PATH, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# ── lista blanca (sin base) ─────────────────────────────────────────────────────────────────────────────────────
def test_lista_blanca_del_repo():
    from ontology import api as A
    pk = A._import_packages()
    assert PKG in pk and pk[PKG] == PKG_PATH
    assert all(os.path.basename(p).startswith('bundle_') and p.endswith('.json.gz') for p in pk.values())


@pytest.mark.parametrize('name', BAD_NAMES + [None, 123])
def test_sin_traversal_ni_otros_archivos(name):
    from ontology import api as A
    with pytest.raises(Exception) as e:
        A._import_package(name)
    assert getattr(e.value, 'code', None) == 'package_not_found'


def test_enlaces_simbolicos_y_carpetas_raras_no_entran(tmp_path, monkeypatch):
    from ontology import api as A
    root = tmp_path / 'lotes'
    good = root / '2030-01-01'
    good.mkdir(parents=True)
    payload = json.dumps({'schema': 'khipus.import/1', 'batch': 'b', 'records': [], 'updates': []}).encode()
    (good / 'bundle_lote9_x.json.gz').write_bytes(gzip.compress(payload))
    (good / 'bundle_otro.json').write_bytes(payload)                       # sin .gz: no es un paquete
    (good / 'notbundle_x.json.gz').write_bytes(gzip.compress(payload))
    (root / 'no-fecha').mkdir()
    (root / 'no-fecha' / 'bundle_y.json.gz').write_bytes(gzip.compress(payload))
    secret = tmp_path / 'secreto'
    secret.mkdir()
    (secret / 'bundle_z.json.gz').write_bytes(gzip.compress(payload))
    os.symlink(secret, root / '2030-01-02')                                 # carpeta enlazada fuera de lotes/
    os.symlink(secret / 'bundle_z.json.gz', good / 'bundle_link.json.gz')   # archivo enlazado
    monkeypatch.setattr(A, '_PKG_ROOT', str(root))
    A._PKG_CACHE.clear()
    assert list(A._import_packages()) == ['2030-01-01/bundle_lote9_x.json.gz']
    b, sha, meta = A._import_package('2030-01-01/bundle_lote9_x.json.gz')
    assert sha == hashlib.sha256(payload).hexdigest() and meta['title_es'].startswith('Lote 9') and meta['n_records'] == 0
    for bad in ('2030-01-02/bundle_z.json.gz', '2030-01-01/bundle_link.json.gz', 'no-fecha/bundle_y.json.gz'):
        with pytest.raises(Exception) as e:
            A._import_package(bad)
        assert e.value.code == 'package_not_found'
    A._PKG_CACHE.clear()


def test_paquete_bomba_se_corta(tmp_path, monkeypatch):
    from ontology import api as A
    root = tmp_path / 'lotes' / '2030-01-01'
    root.mkdir(parents=True)
    (root / 'bundle_grande.json.gz').write_bytes(gzip.compress(b'[' + b' ' * 5000 + b']'))
    monkeypatch.setattr(A, '_PKG_ROOT', str(tmp_path / 'lotes'))
    monkeypatch.setattr(A, '_PKG_MAX_BYTES', 1000)
    A._PKG_CACHE.clear()
    with pytest.raises(Exception) as e:
        A._import_package('2030-01-01/bundle_grande.json.gz')
    assert e.value.code == 'package_too_big'
    A._PKG_CACHE.clear()


def test_meta_del_lote2():
    from ontology import api as A
    A._PKG_CACHE.clear()
    b, sha, meta = A._import_package(PKG)
    assert sha == _pkg_sha() and meta['sha256'] == sha
    assert meta['title_es'] == 'Lote 2 — 386 empresas completas' and meta['title_en'] == 'Batch 2 — 386 complete companies'
    assert meta['n_records'] == 386 and meta['n_relations'] == 2445 and meta['date'] == '2026-10-15'
    assert meta['origin']['excluded'] == 9 and meta['sanitize']['fields_dropped'] == 6 and meta['sanitize']['rejected'] == 0
    assert meta['plan_doc'] == 'docs/expansion/LOTE_2026-10-15_PLAN.md'
    b2, _sha2, _m2 = A._import_package(PKG)
    assert b2 is b                                                         # caché por mtime + tamaño


# ── rutas sobre Postgres ────────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL (Postgres)')
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


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setenv('TRADE_PIN', PIN)
    import server
    from core import http as h
    from core import pin as _pin
    from ontology import api as A
    _pin._reset_for_tests()
    with h._rate_lock:
        h._rate_buckets.clear()
    A._IMPORT_PLAN_CACHE.update(key=None, plan=None)
    _rebuild()
    return server.app.test_client()


def _dbname():
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        return s.execute(text('SELECT current_database()')).scalar()


def _decisions(kind):
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        return s.execute(text('select count(*) from decisions where kind = :k'), {'k': kind}).scalar()


@needs_db
def test_lista_y_plan_sin_pin(client):
    r = client.get('/api/ontology/import/packages')
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    pk = {p['name']: p for p in r.get_json()['packages']}
    assert PKG in pk and pk[PKG]['applied'] is False and pk[PKG]['runs'] == [] and pk[PKG]['sha256'] == _pkg_sha()
    r = client.get('/api/ontology/import/packages/plan', query_string={'package': PKG})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    d = r.get_json()
    p = d['plan']
    assert d['file_sha'] == _pkg_sha() and d['package']['name'] == PKG
    assert p['counts']['valid'] == 386 and p['counts']['invalid'] == 0
    assert p['counts']['create'] + p['counts']['merge'] + p['counts']['update'] + p['counts']['skip'] == 386
    assert p['counts']['merge'] >= 10 and len(p['merges']) == p['counts']['merge']
    assert p['graph_source'] == 'pg' and len(p['plan_sha']) == 64
    wc = p['what_changes']
    assert wc['available'] and wc['before']['tsmc_hit'] == 318 and wc['after']['tsmc_hit'] >= 318 and wc['calibration_stale']
    assert 'items' not in p and len(json.dumps(p)) < 60000                       # resumen CORTO (el plan entero pesa ~8 MB)
    assert set(p['links_by_type']) >= {'supply', 'owns'} and p['not_live_reasons'].get('counterparty_unknown', 0) > 0
    # la misma huella que POST /import/plan {package} con PIN (y sin PIN esa ruta no entra)
    r2 = client.post('/api/ontology/import/plan', json={'package': PKG}, headers=H)
    assert r2.status_code == 200 and r2.get_json()['plan']['plan_sha'] == p['plan_sha']
    r3 = client.post('/api/ontology/import/plan', json={'package': PKG, 'view': 'panel'}, headers=H)
    assert r3.status_code == 200 and r3.get_json()['plan']['plan_sha'] == p['plan_sha'] and 'merges' in r3.get_json()['plan']
    assert client.post('/api/ontology/import/plan', json={'package': PKG}).status_code in (401, 403)
    # y la misma que company_import.plan sobre la vista vigente
    from core.hotviews import hot
    from ontology import company_import as CI
    b = CI.load_bundle(PKG_PATH)
    assert CI.plan(b['records'], b['updates'], view=hot.graph(), batch=b['batch'], what_changes=False)['plan_sha'] == p['plan_sha']


@needs_db
@pytest.mark.parametrize('name', BAD_NAMES)
def test_plan_rechaza_nombres_fuera_de_la_lista(client, name):
    r = client.get('/api/ontology/import/packages/plan', query_string={'package': name})
    assert r.status_code == 404 and r.get_json()['code'] == 'package_not_found'
    r = client.post('/api/ontology/import/apply', json={'package': name, 'expect': {'plan_sha': '0' * 64},
                                                         'confirm_db': _dbname()}, headers=H)
    assert r.status_code in (400, 404)
    if name.strip():
        assert r.get_json()['code'] == 'package_not_found'


@needs_db
def test_una_sola_fuente(client):
    r = client.post('/api/ontology/import/plan', json={'package': PKG, 'file_sha': 'a' * 64}, headers=H)
    assert r.status_code == 400 and r.get_json()['code'] == 'ambiguous_source'
    r = client.post('/api/ontology/import/plan', json={'package': PKG, 'records': []}, headers=H)
    assert r.status_code == 400 and r.get_json()['code'] == 'ambiguous_source'


@needs_db
def test_sanitize_repara_una_ficha_cruda(client):
    from ontology import company_import as CI
    raw_lines = CI._read_lines_gz(os.path.join(ROOT, 'data', 'import', 'lotes', '2026-10-15', 'fichas_completas.jsonl.gz'))
    raw = None
    for ln in raw_lines:
        rec = json.loads(ln)
        _ok, bad = CI.validate_batch([rec])
        if bad:
            raw = rec
            break
    assert raw is not None
    r = client.post('/api/ontology/import/plan', json={'records': [raw], 'view': 'panel'}, headers=H)
    assert r.status_code == 200 and r.get_json()['plan']['counts']['invalid'] == 1
    r = client.post('/api/ontology/import/plan', json={'records': [raw], 'view': 'panel', 'sanitize': 1}, headers=H)
    p = r.get_json()['plan']
    assert r.status_code == 200 and p['counts']['invalid'] == 0 and p['counts']['valid'] == 1
    assert p['sanitize'] and p['sanitize']['records_changed'] == 1


@needs_db
def test_aplicar_y_deshacer_el_paquete_con_pin(client):
    from sqlalchemy import text

    from ontology.db import session_scope
    v0 = _rebuild()
    nodes0 = {n['id'] for n in v0.nodes}
    plan = client.get('/api/ontology/import/packages/plan', query_string={'package': PKG}).get_json()['plan']
    body = {'package': PKG, 'expect': {'plan_sha': plan['plan_sha']}, 'confirm_db': _dbname(), 'actor': 'pytest-panel'}
    assert client.post('/api/ontology/import/apply', json=body).status_code in (401, 403)          # sin PIN nunca entra
    r = client.post('/api/ontology/import/apply', json={**body, 'expect': {'plan_sha': 'f' * 64}}, headers=H)
    assert r.status_code == 409 and r.get_json()['code'] == 'plan_changed'
    r = client.post('/api/ontology/import/apply', json={**body, 'confirm_db': 'otra_base'}, headers=H)
    assert r.status_code == 400 and r.get_json()['code'] == 'confirm_db'
    assert _dbname() in r.get_json()['error']             # tras el PIN, el servidor dice el nombre que espera (el panel lo ofrece)
    d0 = _decisions('ontology.bulk_import')
    r = client.post('/api/ontology/import/apply', json=body, headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:400]
    res = r.get_json()
    assert res['status'] == 'ok' and res['decision_id'] and res['run_id']
    assert res['plan_counts'] == plan['counts'] and res['links_created'] > 0       # el panel muestra EMPRESAS del plan
    assert res['objects_created'] == plan['counts']['create'] + plan['counts']['sources_new']   # (+ las fuentes nuevas)
    assert _decisions('ontology.bulk_import') == d0 + 1
    with session_scope() as s:
        row = s.execute(text('select file_sha, batch from import_runs where kind = :k order by created_at desc limit 1'),
                        {'k': 'apply'}).one()
    assert row[0] == _pkg_sha() and row[1] == 'lote-2026-10-15-completas'
    pk = {p['name']: p for p in client.get('/api/ontology/import/packages').get_json()['packages']}
    assert pk[PKG]['applied'] is True and pk[PKG]['runs'][0]['run_id'] == res['run_id']
    v1 = _rebuild()
    assert len(v1.nodes) == len(v0.nodes) + plan['counts']['create']
    # deshacer por la API con PIN (lo que hace el botón «Deshacer» del panel)
    rb = {'run_id': res['run_id'], 'confirm_db': _dbname(), 'actor': 'pytest-panel'}
    assert client.post('/api/ontology/import/rollback', json=rb).status_code in (401, 403)
    r = client.post('/api/ontology/import/rollback', json=rb, headers=H)
    assert r.status_code == 200, r.get_data(as_text=True)[:400]
    assert r.get_json()['decision_id'] and r.get_json()['objects_retired'] == plan['counts']['create']
    r = client.post('/api/ontology/import/rollback', json=rb, headers=H)
    assert r.status_code == 409 and r.get_json()['code'] == 'already_rolled_back'
    pk = {p['name']: p for p in client.get('/api/ontology/import/packages').get_json()['packages']}
    assert pk[PKG]['applied'] is False and pk[PKG]['runs'][0]['undone'] is True
    v2 = _rebuild()
    assert {n['id'] for n in v2.nodes} == nodes0 and v2.impact.stats['TSMC']['reach_1'] == 318
