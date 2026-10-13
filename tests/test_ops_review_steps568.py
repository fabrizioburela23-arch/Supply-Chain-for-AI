"""tests/test_ops_review_steps568.py — revisión adversarial de los pasos 5, 6 y 8 (INFRA_OPERATIVA).

Cada prueba reproduce un hallazgo verificado y falla con el código anterior:
  · rutas SIN PIN (POST /api/matrix/simulations, /api/ontology/ingest/news) escribían el 'actor' libre en
    events.actor: 'op:fabrizio' tecleado parecía una escritura del operador (y se sellaba en el libro);
  · /api/ontology/agents/cycle con force:true seguía abierto en PRODUCCIÓN sin TRADE_PIN (G-6);
  · aprobar un memo del comité (camino de DINERO) y crear/revocar tokens MCP registraban el nombre libre;
  · identity.legacy() aceptaba 120 caracteres y decisions.declared_name es String(80): la Acción se revertía;
  · el sello del libro dependía del TimeZone de la sesión (verify marcaba TODO como cambiado);
  · decisions.approve(): op:fabrizio no podía aprobar lo que él mismo pidió (D1) y se podía aprobar dos veces
    o aprobar algo ya ejecutado;
  · el chat citaba el snapshot como fuente aunque los datos vinieran de Postgres.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PIN = 'pin-revision-5168'
PROD_VARS = ('RAILWAY_ENVIRONMENT', 'RAILWAY_ENVIRONMENT_NAME', 'RAILWAY_PROJECT_ID')


@pytest.fixture
def clean(monkeypatch):
    from core import http as h
    from core import pin
    for v in PROD_VARS:
        monkeypatch.delenv(v, raising=False)
    pin._reset_for_tests()
    with h._rate_lock:
        h._rate_buckets.clear()
    yield
    pin._reset_for_tests()


@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    with session_scope() as s:
        for oid in ('RV_A', 'nvidia'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=oid)
    yield engine
    Base.metadata.drop_all(engine)


def _app(*bps):
    from flask import Flask
    app = Flask('review568')
    app.config['TESTING'] = True
    for bp in bps:
        app.register_blueprint(bp)
    return app.test_client()


# ── 1. rutas sin PIN no pueden escribir un principal reservado ───────────────
@needs_db
def test_simulacion_sin_pin_no_se_hace_pasar_por_el_operador(db, monkeypatch, clean):
    from sqlalchemy import select

    from matrix.api import matrix_bp
    from ontology.db import session_scope
    from ontology.models import Event
    monkeypatch.setenv('TRADE_PIN', PIN)
    monkeypatch.setenv('RAILWAY_ENVIRONMENT', 'production')
    r = _app(matrix_bp).post('/api/matrix/simulations',
                             json={'actor': 'op:fabrizio', 'name': 'x', 'targets': ['nvidia']})
    assert r.status_code == 200, r.get_json()
    sid = r.get_json()['id']
    with session_scope() as s:
        ev = s.scalars(select(Event).where(Event.object_id == sid)).first()
        assert ev.actor == 'ui:anon'
        assert ev.payload['properties']['saved_by'] == 'op:fabrizio'          # solo como etiqueta
        assert ev.payload['properties']['saved_by_principal'] == 'ui:anon'
        assert not s.scalars(select(Event).where(Event.actor.like('op:%'), Event.source == 'livesim')).first()


@needs_db
def test_simulacion_con_pin_queda_del_operador(db, monkeypatch, clean):
    from sqlalchemy import select

    from matrix.api import matrix_bp
    from ontology.db import session_scope
    from ontology.models import Event
    monkeypatch.setenv('TRADE_PIN', PIN)
    # la ruta no exige PIN; si alguien lo verificó en esta petición (pin.check), cuenta. Sin verificar: ui:anon
    r = _app(matrix_bp).post('/api/matrix/simulations', headers={'X-Trade-Pin': PIN},
                             json={'actor': 'Fabrizio', 'name': 'y', 'targets': ['nvidia']})
    assert r.status_code == 200
    with session_scope() as s:
        ev = s.scalars(select(Event).where(Event.object_id == r.get_json()['id'])).first()
        assert ev.actor == 'ui:anon'          # el header sin verificar NO autentica (nunca se compara aquí)


@needs_db
def test_ingesta_de_noticias_registra_el_principal(db, monkeypatch, clean):
    import ontology.ingest_news as ing
    from ontology.api import ontology_bp
    seen = {}

    def fake(session, entity_id, query=None, limit=10, actor=None, provider_registry=None):
        seen['actor'] = actor
        return {'ok': True, 'new': 0}
    monkeypatch.setattr(ing, 'ingest_news_for', fake)
    r = _app(ontology_bp).post('/api/ontology/ingest/news', json={'entity_id': 'RV_A', 'actor': 'op:fabrizio'})
    assert r.status_code == 200, r.get_json()
    assert seen['actor'] == 'ui:anon'
    r = _app(ontology_bp).post('/api/ontology/ingest/news', json={'entity_id': 'RV_A'})
    assert r.status_code == 400                                           # sigue exigiendo una etiqueta


# ── 2. agents/cycle force en producción sin TRADE_PIN ────────────────────────
def test_ciclo_forzado_en_produccion_sin_pin_configurado_da_403(monkeypatch, clean):
    import ontology.api as oapi
    calls = []
    monkeypatch.setattr(oapi, 'ontology_available', lambda: True)
    monkeypatch.setattr(oapi, '_try_start_cycle', lambda force: calls.append(force) or False)
    monkeypatch.delenv('TRADE_PIN', raising=False)
    monkeypatch.setenv('RAILWAY_ENVIRONMENT', 'production')
    c = _app(oapi.ontology_bp)
    r = c.post('/api/ontology/agents/cycle', json={'force': True})
    assert r.status_code == 403, r.get_json()
    assert calls == []
    r = c.post('/api/ontology/agents/cycle', json={})                    # el latido normal sigue
    assert r.status_code == 200 and calls == [False]
    # en desarrollo (sin RAILWAY_*) forzar sin PIN sigue permitido, como las demás escrituras de operador
    monkeypatch.delenv('RAILWAY_ENVIRONMENT')
    r = c.post('/api/ontology/agents/cycle', json={'force': True})
    assert r.status_code == 200 and calls == [False, True]


# ── 3. camino de dinero: comité y tokens MCP registran el principal ──────────
@needs_db
def test_aprobar_memo_del_comite_registra_el_principal(db, monkeypatch, clean):
    import research.committee as rc
    from research.committee_api import committee_bp
    seen = {}

    def fake_approve(s, mid, actor, note=''):
        seen['actor'] = actor
        return {'ok': True}
    monkeypatch.setattr(rc, 'approve_memo', fake_approve)
    monkeypatch.setenv('TRADE_PIN', PIN)
    c = _app(committee_bp)
    r = c.post('/api/committee/memo/m1/approve', headers={'X-Trade-Pin': PIN},
               json={'actor': 'Alice (compliance)'})
    assert r.status_code == 200, r.get_json()
    assert seen['actor'] == 'op:fabrizio'
    r = c.post('/api/committee/memo/m1/approve', headers={'X-Trade-Pin': PIN}, json={})
    assert r.status_code == 400                                           # la etiqueta sigue siendo obligatoria


@needs_db
def test_token_mcp_registra_el_principal_como_creador_y_revocador(db, monkeypatch, clean):
    from mcp_server import auth as mauth
    from mcp_server.api import mcp_bp
    monkeypatch.setenv('TRADE_PIN', PIN)
    mauth._reset_for_tests() if hasattr(mauth, '_reset_for_tests') else None
    c = _app(mcp_bp)
    r = c.post('/api/mcp/tokens', headers={'X-Trade-Pin': PIN},
               json={'actor': 'otra-persona', 'name': 'rev568', 'scopes': ['read', 'research']})
    assert r.status_code == 201, r.get_json()
    d = r.get_json()
    assert d['created_by'] == 'op:fabrizio'
    r = c.post(f"/api/mcp/tokens/{d['id']}/revoke", headers={'X-Trade-Pin': PIN, 'X-Khipu-Actor': 'alguien'},
               json={})
    assert r.status_code == 200, r.get_json()
    from ontology.db import session_scope
    with session_scope() as s:
        row = [t for t in mauth.list_tokens(s) if t['id'] == d['id']][0]
    assert row['revoked_by'] == 'op:fabrizio'


# ── 4. etiqueta larga: la Acción no se revierte ──────────────────────────────
def test_legacy_recorta_la_etiqueta_al_largo_de_la_columna():
    from core import identity
    p = identity.legacy('y' * 200)
    assert len(p.declared_name) == 80 and len(p.id) <= 96


@needs_db
def test_accion_con_actor_largo_se_registra(db):
    from core import decisions
    from ontology.actions import execute_action
    from ontology.db import session_scope
    # 81-120 caracteres: cabe en events.actor (String(120)) pero no en decisions.declared_name (String(80))
    actor = 'Analista de riesgos del equipo de cumplimiento regulatorio - revisión trimestral Q3 / equipo B'
    assert 80 < len(actor) <= 120
    meta = {}
    with session_scope() as s:
        execute_action(s, 'AnotarObjeto', {'object_id': 'RV_A', 'texto': 'hola'}, actor, meta=meta)
    with session_scope() as s:
        dec = decisions.get(s, meta['decision_id'], redact=False)
    assert dec['status'] == 'executed' and len(dec['declared_name']) <= 80


# ── 5. el sello no depende del TimeZone de la sesión ─────────────────────────
@needs_db
def test_verify_no_depende_del_timezone_de_la_sesion(db):
    from sqlalchemy import create_engine, text

    from core import ledger
    from ontology.actions import execute_action
    from ontology.db import _normalize_url, session_scope
    for i in range(3):
        with session_scope() as s:
            execute_action(s, 'AnotarObjeto', {'object_id': 'RV_A', 'texto': f'tz {i}'}, 'pytest')
    lima = create_engine(_normalize_url(DATABASE_URL), connect_args={'options': '-c timezone=America/Lima'})
    try:
        with lima.connect() as c:
            assert c.execute(text('SHOW TimeZone')).scalar() == 'America/Lima'
        out = ledger.seal(engine=lima)                                    # sellar en Lima…
        assert out.get('sealed', 0) > 0
        v = ledger.verify()                                               # …verificar con la zona por defecto
        assert v['ok'], v['broken'][:3]
        assert ledger.verify(engine=lima)['ok']
    finally:
        lima.dispose()


# ── 6. aprobar: D1 (un solo aprobador) y una sola vez ────────────────────────
@needs_db
def test_operador_aprueba_lo_que_pidio_una_sola_vez(db):
    from core import decisions, identity
    from ontology.db import session_scope
    op = identity.operator('ui', 'Fabrizio')
    with session_scope() as s:
        with decisions.decision_scope('proposal.create', op, session=s, subject={'entity_ids': ['RV_A']}) as ctx:
            ctx.output = {'proposal': 'x'}
            ctx.status = 'pending_approval'
        target = ctx.id
    with session_scope() as s:
        gid = decisions.approve(s, target, op)                            # D1: el mismo operador SÍ aprueba
    assert gid
    with session_scope() as s:
        with pytest.raises(ValueError):                                   # una segunda aprobación: no
            decisions.approve(s, target, op)
    with session_scope() as s:
        with pytest.raises(ValueError):
            decisions.approve(s, target, op, verdict='deny')
    # algo ya ejecutado no espera aprobación
    with session_scope() as s:
        with decisions.decision_scope('proposal.create', op, session=s, subject={'entity_ids': ['RV_A']}) as ctx:
            ctx.output = {'x': 1}
            ctx.status = 'executed'
        done = ctx.id
    with session_scope() as s:
        with pytest.raises(ValueError):
            decisions.approve(s, done, op)
    # un agente/sistema sigue sin poder aprobar
    with session_scope() as s:
        with pytest.raises(PermissionError):
            decisions.approve(s, target, identity.system('otro'))


# ── 7. el chat cita la fuente real de la generación ──────────────────────────
def test_rank_companies_cita_la_fuente_de_la_generacion():
    from core import khipu_chat
    from mcp_server import tools
    out = khipu_chat.x_rank_companies()
    assert out['source'] == tools._snapshot()['source_label']
    src = open(os.path.join(ROOT, 'core', 'khipu_chat.py'), encoding='utf-8').read()
    assert "'source': mt.SNAPSHOT_SOURCE," not in src
