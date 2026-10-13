"""tests/test_governance.py — INFRA_OPERATIVA paso 9: registro de gobernanza (core/governance, scripts/build_governance).

Garantiza (docs/INFRA_OPERATIVA.md §5.1-§5.4, decisiones D1/D2):
  · los archivos de governance/artifacts == manifest.json (`--check`), los espejos (pesos α del vocabulario,
    vocabulario de decisiones, hash del vocabulario) coinciden y un artefacto NO cambia con la misma versión;
  · lint de semver: un PATCH que cambia un número se rechaza; un MINOR que quita/cambia se rechaza; MAJOR pasa;
  · D2: FRAGILITY_CAP / IMPORT_BULK_WEIGHT_FACTOR / DECIDE_MIN_CONF / COMMITTEE_MEMO_TTL_HOURS ya NO cambian el
    número (avisan en el 🩺); `<ARTEFACTO>=<semver>` solo elige una versión existente/aprobada;
  · con base: bootstrap 1.0.0 (ratified=false) con los artefactos del repo + decisiones governance.propose y
    governance.activate; ratificar exige PIN (decisión governance.ratify); gov_* append-only; un release nuevo en
    la base CAMBIA las constantes de los módulos (y GOV_RELEASE vuelve a uno ratificado); un cuerpo manipulado
    no entra en vigor;
  · los eventos y las decisiones llevan el release_hash vigente; el ETag de /api/vocabulary es el hash del
    artefacto ontology.schema; /api/governance/active con ETag/304.
"""
import json
import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


# ── repositorio ──────────────────────────────────────────────────────────────
def test_build_governance_check_al_dia():
    from scripts import build_governance as B
    assert B.check(verbose=False) == []


@pytest.fixture()
def repo_copy(tmp_path, monkeypatch):
    """Copia de governance/ en un tmp: las pruebas que lo rompen no tocan el repo."""
    from core import governance as G
    dst = tmp_path / 'governance'
    shutil.copytree(os.path.join(ROOT, 'governance', 'artifacts'), dst / 'artifacts')
    shutil.copy(os.path.join(ROOT, 'governance', 'manifest.json'), dst / 'manifest.json')
    monkeypatch.setattr(G, 'ART_DIR', str(dst / 'artifacts'))
    monkeypatch.setattr(G, 'MANIFEST_PATH', str(dst / 'manifest.json'))
    G._STATE['repo'] = None
    yield dst
    G._STATE['repo'] = None


def _edit(path, fn):
    with open(path, encoding='utf-8') as fh:
        d = json.load(fh)
    fn(d)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(d, fh, ensure_ascii=False, indent=2)
    return d


def test_mismo_semver_con_otro_contenido_se_rechaza(repo_copy):
    from scripts import build_governance as B
    _edit(repo_copy / 'artifacts' / 'kernel.params@1.0.0.json', lambda d: d['params'].update(sole_link_floor=5.0))
    probs = B.check(verbose=False)
    assert any('CAMBIÓ de contenido con la misma versión' in p for p in probs)
    with pytest.raises(SystemExit):
        B.write()
    from core import governance as G
    with pytest.raises(G.GovernanceError):
        G.repo_bundle()                          # el arranque tampoco acepta un artefacto cambiado en silencio


def test_changelog_no_cambia_el_hash(repo_copy):
    from scripts import build_governance as B
    _edit(repo_copy / 'artifacts' / 'kernel.params@1.0.0.json', lambda d: d.update(changelog_en='typo fixed'))
    assert B.check(verbose=False) == []


def _new_version(repo_copy, change_kind, mutate, semver='1.0.1'):
    src = repo_copy / 'artifacts' / 'policy.committee@1.0.0.json'
    with open(src, encoding='utf-8') as fh:
        d = json.load(fh)
    d.update(semver=semver, change_kind=change_kind, parent='policy.committee@1.0.0',
             changelog_es='prueba', changelog_en='test')
    mutate(d['params'])
    with open(repo_copy / 'artifacts' / f'policy.committee@{semver}.json', 'w', encoding='utf-8') as fh:
        json.dump(d, fh, ensure_ascii=False, indent=2)


def test_semver_patch_que_cambia_un_numero_se_rechaza(repo_copy):
    from scripts import build_governance as B
    _new_version(repo_copy, 'patch', lambda p: p.update(buy_threshold=30.0))
    assert any('PATCH no puede cambiar' in p for p in B.semver_problems(B.G.scan_repo()))


def test_semver_minor_solo_agrega(repo_copy):
    from scripts import build_governance as B
    _new_version(repo_copy, 'minor', lambda p: p.pop('min_claims'), semver='1.1.0')
    assert any('MINOR solo agrega' in p for p in B.semver_problems(B.G.scan_repo()))


def test_semver_minor_que_agrega_y_major_pasan(repo_copy):
    from scripts import build_governance as B
    _new_version(repo_copy, 'minor', lambda p: p.update(nueva_clave=1), semver='1.1.0')
    _new_version(repo_copy, 'major', lambda p: p.update(buy_threshold=30.0), semver='2.0.0')
    assert B.semver_problems(B.G.scan_repo()) == []
    B.write()
    assert B.check(verbose=False) == []
    from core import governance as G
    G._STATE['repo'] = None
    assert G.repo_bundle().artifacts['policy.committee']['semver'] == '2.0.0'   # el repo PROPONE la más alta


def test_espejo_de_pesos_del_vocabulario(repo_copy, monkeypatch):
    from ontology import vocabulary as vocab
    from scripts import build_governance as B
    w = dict(vocab.relation_weights())
    w['license'] = 0.8
    monkeypatch.setattr(vocab, 'relation_weights', lambda: w)
    assert any('rel_weights' in p for p in B.check(verbose=False))


def test_ledger_kinds_es_espejo_de_decisions():
    from core import decisions, governance
    assert sorted(decisions.KINDS) == governance.param('ledger.kinds', 'kinds')
    assert 'governance.ratify' in decisions.KINDS and 'ledger.chain_break' in decisions.KINDS


# ── D2: el entorno no fija números ───────────────────────────────────────────
def test_variables_numericas_viejas_no_mandan_y_avisan(monkeypatch):
    from core import governance
    from matrix import engine as E
    monkeypatch.setenv('FRAGILITY_CAP', '9')
    monkeypatch.setenv('IMPORT_BULK_WEIGHT_FACTOR', '1.0')
    monkeypatch.setenv('DECIDE_MIN_CONF', '0.1')
    monkeypatch.setenv('COMMITTEE_MEMO_TTL_HOURS', '1')
    assert E.fragility_cap() == 2.5 and E.bulk_weight_factor() == 0.5
    from research import committee as C
    assert C._ttl_hours() == 72.0
    warns = {w['env'] for w in governance.env_warnings()}
    assert warns == {'FRAGILITY_CAP', 'IMPORT_BULK_WEIGHT_FACTOR', 'DECIDE_MIN_CONF', 'COMMITTEE_MEMO_TTL_HOURS'}
    w = next(x for x in governance.env_warnings() if x['env'] == 'FRAGILITY_CAP')
    assert w['es'] and w['en'] and w['in_force'] == 2.5
    monkeypatch.setenv('FRAGILITY_CAP', '2.5')             # igual al artefacto → sin aviso
    assert 'FRAGILITY_CAP' not in {x['env'] for x in governance.env_warnings()}


def test_seleccion_por_entorno_solo_versiones_existentes(monkeypatch):
    from core import governance as G
    monkeypatch.setenv('KERNEL_PARAMS', '9.9.9')
    G._STATE['repo'] = None
    try:
        assert G.repo_bundle().artifacts['kernel.params']['semver'] == '1.0.0'   # no existe → se ignora
        assert G.repo_bundle().selected == {}
    finally:
        monkeypatch.delenv('KERNEL_PARAMS')
        G._STATE['repo'] = None


def test_sin_base_rige_el_repositorio(monkeypatch):
    import ontology.db as odb

    from core import governance
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    rh, label = governance.release()
    assert label == 'repo-unapproved' and len(rh) == 64
    assert rh == governance.repo_bundle().release_hash
    from core.hotviews import signals
    assert signals.release_hash() == (rh, label)


def test_etag_del_vocabulario_es_el_hash_del_artefacto():
    import server
    from core import governance
    c = server.app.test_client()
    r = c.get('/api/vocabulary')
    assert r.status_code == 200
    assert r.headers['ETag'] == f'"vocab-{governance.artifact_hash_of("ontology.schema")[:16]}"'


def test_api_active_con_etag(monkeypatch):
    import ontology.db as odb
    import server
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    c = server.app.test_client()
    r = c.get('/api/governance/active')
    assert r.status_code == 200
    d = r.get_json()
    assert d['artifacts']['kernel.params']['params']['sole_link_floor'] == 6.0
    assert d['explain']['es'] and d['explain']['en']
    r2 = c.get('/api/governance/active', headers={'If-None-Match': r.headers['ETag']})
    assert r2.status_code == 304
    st = c.get('/api/governance/status').get_json()
    assert isinstance(st['env_warnings'], int) and 'db_error' not in st


# ── con base ─────────────────────────────────────────────────────────────────
@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from core import governance
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    governance._reset_for_tests()
    assert init_schema(retries=1)
    yield engine
    governance._reset_for_tests()
    Base.metadata.drop_all(engine)


@needs_db
def test_bootstrap_crea_release_1_0_0_sin_ratificar(db):
    from sqlalchemy import text

    from core import governance
    repo = governance.repo_bundle()
    with db.connect() as c:
        n_art = c.execute(text('SELECT count(*) FROM gov_artifacts')).scalar()
        rel = c.execute(text('SELECT release_hash, semver, ratified, artifacts FROM gov_releases')).all()
        kinds = {k for (k,) in c.execute(text("SELECT kind FROM decisions WHERE kind LIKE 'governance.%'"))}
    assert n_art == len(governance.scan_repo())
    assert len(rel) == 1 and rel[0].release_hash == repo.release_hash and rel[0].semver == '1.0.0'
    assert rel[0].ratified is False
    assert kinds == {'governance.propose', 'governance.activate'}
    st = governance.status()
    assert st['source'] == 'db' and st['label'] == 'db-unratified' and st['needs_ratification'] is True
    assert st['release_hash'] == repo.release_hash
    # idempotente: otro init_schema no duplica nada
    from ontology.db import init_schema
    assert init_schema(retries=1)
    with db.connect() as c:
        assert c.execute(text('SELECT count(*) FROM gov_artifacts')).scalar() == n_art
        assert c.execute(text('SELECT count(*) FROM gov_releases')).scalar() == 1


@needs_db
def test_gov_tablas_append_only(db):
    from sqlalchemy import text
    for sql in ("UPDATE gov_releases SET ratified = true", 'DELETE FROM gov_artifacts', 'TRUNCATE gov_releases'):
        with pytest.raises(Exception) as ei:
            with db.begin() as c:
                c.execute(text(sql))
        assert 'append-only' in str(ei.value)


@needs_db
def test_eventos_y_decisiones_llevan_el_release(db):
    from sqlalchemy import text

    from core import governance, identity
    from ontology.actions import execute_action
    from ontology.db import session_scope
    from ontology.service import apply_event
    with session_scope() as s:
        ev = apply_event(s, 'ObjectCreated', {'label': 'GV_A', 'type': 'Company'}, valid_from='2000-01-01',
                         source='test', actor='pytest', object_id='GV_A')
        eid = ev.id
    meta = {}
    with session_scope() as s:
        execute_action(s, 'AnotarObjeto', {'object_id': 'GV_A', 'texto': 'nota'}, 'op:fabrizio',
                       principal=identity.operator(), meta=meta)
    rh = governance.release()[0]
    with db.connect() as c:
        assert c.execute(text('SELECT release_hash FROM events WHERE id = :i'), {'i': eid}).scalar() == rh
        d = c.execute(text('SELECT release_hash, manifest FROM decisions WHERE id = :i'),
                      {'i': meta['decision_id']}).first()
    assert d.release_hash == rh
    assert d.manifest['release']['semver']['kernel.params'] == '1.0.0'


@needs_db
def test_ratificar_exige_pin_y_queda_como_decision(db, monkeypatch):
    from sqlalchemy import text

    import server
    from core import governance, pin
    monkeypatch.setenv('TRADE_PIN', 'pin-gov-12345')
    pin._reset_for_tests()
    c = server.app.test_client()
    assert c.post('/api/governance/ratify', json={}).status_code == 401
    r = c.post('/api/governance/ratify', json={'note': 'revisado'}, headers={'X-Trade-Pin': 'pin-gov-12345'})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()['status'] == 'db'
    assert governance.status()['ratified'] is True and governance.status()['needs_ratification'] is False
    r = c.post('/api/governance/ratify', json={}, headers={'X-Trade-Pin': 'pin-gov-12345'})
    assert r.status_code == 409
    with db.connect() as cn:
        row = cn.execute(text("SELECT principal_id, auth, status FROM decisions WHERE kind = 'governance.ratify'")).first()
    assert row.principal_id == 'op:fabrizio' and row.auth == 'pin' and row.status == 'approved'
    full = c.get('/api/governance/status', headers={'X-Trade-Pin': 'pin-gov-12345'}).get_json()
    assert isinstance(full['env_warnings'], list)


def _insert_release(db, params_patch, semver_art='8.0.0', rel_semver='2.0.0', tamper=False):
    # (kernel.params@2.0.0 ya existe de verdad en el repositorio desde el paso 12: la prueba usa otra versión)
    from sqlalchemy import text

    from core import governance as G
    base = G.repo_bundle()
    doc = json.loads(json.dumps({'id': 'kernel.params', 'semver': semver_art, 'kind': 'params',
                                 'params': dict(base.artifacts['kernel.params']['params'], **params_patch)}))
    h = G.artifact_hash(doc)
    body = dict(doc)
    if tamper:
        body['params'] = dict(body['params'], sole_link_floor=99.0)
    arts = {a: {'hash': v['hash'], 'semver': v['semver']} for a, v in base.artifacts.items()}
    arts['kernel.params'] = {'hash': h, 'semver': semver_art}
    rh = G.release_hash_of({a: v['hash'] for a, v in arts.items()})
    with db.begin() as c:
        c.execute(text(
            "INSERT INTO gov_artifacts (hash, artifact_id, semver, change_kind, body, changelog_es, changelog_en, "
            "proposed_by, proposal_decision_id) VALUES (:h, 'kernel.params', :v, 'major', CAST(:b AS jsonb), 'p', 'p', "
            "'test', gen_random_uuid())"), {'h': h, 'v': semver_art, 'b': json.dumps(body)})
        c.execute(text(
            "INSERT INTO gov_releases (release_hash, semver, artifacts, effective_from, approval_decision_id, ratified) "
            "VALUES (:r, :v, CAST(:a AS jsonb), clock_timestamp(), gen_random_uuid(), true)"),
            {'r': rh, 'v': rel_semver, 'a': json.dumps(arts)})
    return rh


@needs_db
def test_release_nuevo_en_la_base_cambia_las_constantes(db, monkeypatch):
    from core import governance
    from matrix import engine as E
    from matrix import tensor as T
    old = governance.release()[0]
    rh = _insert_release(db, {'sole_link_floor': 5.0, 'damping': 0.5})
    try:
        b = governance.refresh()
        assert b is not None and b.release_hash == rh and governance.release() == (rh, 'db')
        assert E.SOLE_LINK_FLOOR == 5.0 and E.DAMPING == 0.5 and T.DAMPING == 0.5
        # GOV_RELEASE vuelve a un release RATIFICADO (el bootstrap, ratificado en la prueba anterior)
        monkeypatch.setenv('GOV_RELEASE', old[:16])
        governance.refresh()
        assert governance.release() == (old, 'db-selected') and E.SOLE_LINK_FLOOR == 6.0
        monkeypatch.setenv('GOV_RELEASE', 'deadbeefdeadbeef')        # inexistente → se ignora (rige el último)
        governance.refresh()
        assert governance.release()[0] == rh
    finally:
        monkeypatch.delenv('GOV_RELEASE', raising=False)


@needs_db
def test_cuerpo_manipulado_no_entra_en_vigor(db):
    from core import governance
    from matrix import engine as E
    before = governance.release()[0]
    floor_before = E.SOLE_LINK_FLOOR
    _insert_release(db, {'sole_link_floor': 4.0}, semver_art='3.0.0', rel_semver='3.0.0', tamper=True)
    assert governance.refresh() is None
    assert governance.release()[0] == before and E.SOLE_LINK_FLOOR == floor_before
    assert 'no coincide con su hash' in (governance.status()['db_error'] or '')


# ── paso 25: el lint del script y el de la app son EL MISMO (bilingüe) ──────
def test_lint_bilingue_compartido_con_la_app(repo_copy):
    from core import governance_lint as GL
    from scripts import build_governance as B
    _new_version(repo_copy, 'minor', lambda p: p.update(buy_threshold=30.0), semver='1.1.0')
    bi = GL.semver_problems(B.G.scan_repo())
    assert [p['es'] for p in bi] == B.semver_problems(B.G.scan_repo())
    assert bi and all(p['en'] and p['code'] for p in bi)
    assert GL.needed_kind({'a': 1}, {'a': 1, 'b': 2}) == 'minor' and GL.needed_kind({'a': 1}, {'a': 2}) == 'major'
    assert GL.next_semver({'1.0.0', '2.0.0'}, '1.0.0', 'major') == '3.0.0'
    assert GL.next_semver({'1.0.0', '1.1.0'}, '1.0.0', 'minor') == '1.2.0'
