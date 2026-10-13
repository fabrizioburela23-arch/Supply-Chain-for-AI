"""tests/test_review_batch_g.py — revisión del batch G (pasos 22/23/25/26): hallazgos reproducidos y corregidos.

Gobernanza:
  · una variable de Railway (<ARTEFACTO>=<semver>) NUNCA enciende una versión "activation: pin" (guardia en enforce,
    puertas que bloquean): ni sin base ni para un artefacto que el release de la base no trae (fallback);
  · una activación PROGRAMADA cancelada o todavía futura no cuenta como aprobada (GOV_RELEASE / <ARTEFACTO>=…);
  · una programada ya vencida pero que el reloj aún no aplicó no se pisa con otra activación (y queda su 'applies');
  · un MAYOR nuevo exige su regresión registrada; una validation_id de OTRA versión → 409;
  · semver estricto (sin ceros a la izquierda ni dígitos no ASCII).
Libro / guardia:
  · la purga no vacía un contenido que algo citó en los últimos 90 días (system prompt del chat repetido);
  · 'pendientes' de la retención = lo que la próxima purga vaciaría; lo protegido va aparte;
  · caducar propuestas (GET /approvals) y el cambio de cuenta de la casa llevan su decisión (en enforce no fallan).
"""
import hashlib
import os
import sys
import time
import zlib
from datetime import datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PIN = 'pin-revision-g-xyz'


# ── sin base ─────────────────────────────────────────────────────────────────
def test_variable_no_enciende_versiones_pin_sin_base(monkeypatch):
    import ontology.db as odb
    from core import gates, governance, ledger_guard
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    for k in ('POLICY_GUARD', 'POLICY_GATES', 'KERNEL_PARAMS'):
        monkeypatch.setenv(k, '2.0.0')
    governance._reset_for_tests()
    try:
        assert ledger_guard.policy_mode() == 'warn'
        assert gates.mode() == 'shadow'
        assert governance.artifact_semver('kernel.params') == '1.0.0'
        assert governance.repo_bundle().selected == {}
    finally:
        for k in ('POLICY_GUARD', 'POLICY_GATES', 'KERNEL_PARAMS'):
            monkeypatch.delenv(k)
        governance._reset_for_tests()


def test_fallback_de_un_release_de_la_base_ignora_el_entorno(monkeypatch):
    from core import governance, ledger_guard
    governance._reset_for_tests()
    repo = governance.repo_bundle()
    arts = {a: v for a, v in repo.artifacts.items() if a not in ('policy.guard', 'ledger.retention')}
    db_b = governance._bundle(arts, '1.0.0', 'db', 'db', True)       # un release anterior al batch (sin esos dos)
    monkeypatch.setattr(governance, '_db_on', lambda: True)
    monkeypatch.setitem(governance._STATE, 'db', db_b)
    try:
        assert set(governance.fallbacks()) >= {'policy.guard', 'ledger.retention'}
        assert ledger_guard.policy_mode() == 'warn'
        monkeypatch.setenv('POLICY_GUARD', '2.0.0')
        with governance._LOCK:
            governance._STATE['repo'] = None                         # el entorno se relee
        assert ledger_guard.policy_mode() == 'warn'                  # fuera de un release aprobado: nada
        assert governance.fallbacks()['policy.guard']['semver'] == '1.0.0'
    finally:
        monkeypatch.delenv('POLICY_GUARD', raising=False)
        governance._STATE['db'] = None
        governance._reset_for_tests()


def test_semver_estricto_no_registra_duplicados():
    from core import governance as G
    from core import governance_flow as F
    for bad in ('02.0.0', '２.0.0', '2.00.0', '1.0', '2.0.0x'):
        with pytest.raises(G.GovernanceError):
            G.semver_key(bad)
        codes = [p['code'] for p in F.build_proposal('kernel.params', {'damping': 0.55}, semver=bad)[2]]
        assert codes == ['bad_semver'], (bad, codes)
    assert G.semver_key('10.0.0') == (10, 0, 0) and G.semver_key('0.1.0') == (0, 1, 0)


# ── con base ─────────────────────────────────────────────────────────────────
@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from core import governance, governance_flow, ledger_guard
    from core.hotviews import hot, registry
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    governance._reset_for_tests()
    governance_flow.reset_for_tests()
    ledger_guard._reset_for_tests()
    assert init_schema(retries=1)
    yield engine
    from core.hotviews import builder
    t0 = time.time()
    while builder.state().get('building') and time.time() - t0 < 10:
        time.sleep(0.02)
    governance._reset_for_tests()
    governance_flow.reset_for_tests()
    registry.reset()
    hot.reset()
    Base.metadata.drop_all(engine)


def _client(monkeypatch):
    import server
    from core import http as core_http
    from core import pin
    monkeypatch.setenv('TRADE_PIN', PIN)
    pin._reset_for_tests()
    c = server.app.test_client()
    real_post = c.post

    def post(*a, **k):
        core_http._rate_buckets.clear()
        k.setdefault('headers', {'X-Trade-Pin': PIN})
        return real_post(*a, **k)
    c.post = post
    return c


@needs_db
def test_major_sin_regresion_y_validacion_ajena(db, monkeypatch):
    from core import governance, governance_flow, identity
    c = _client(monkeypatch)
    governance.refresh()
    r = c.post('/api/governance/activate', json={'artifact': 'kernel.params', 'semver': '2.0.0'})
    assert r.status_code == 409 and r.get_json()['code'] == 'regression_required' and r.get_json()['error_en']
    other = governance_flow.validate(identity.operator(), 'policy.guard', '2.0.0')['decision_id']
    r = c.post('/api/governance/activate', json={'artifact': 'kernel.params', 'semver': '2.0.0',
                                                 'validation_id': other})
    assert r.status_code == 409 and r.get_json()['code'] == 'validation_mismatch', r.get_json()
    r = c.post('/api/governance/activate', json={'artifact': 'kernel.params', 'semver': '2.0.0',
                                                 'validation_id': 'no-es-un-uuid'})
    assert r.status_code == 409 and r.get_json()['code'] == 'validation_mismatch'
    assert governance.artifact_semver('kernel.params') == '1.0.0'


@needs_db
def test_programada_cancelada_o_futura_no_la_elige_el_entorno(db, monkeypatch):
    from core import governance, governance_flow, identity
    c = _client(monkeypatch)
    governance.refresh()
    boot = governance.active().release_hash
    governance_flow.validate(identity.operator(), 'kernel.params', '2.0.0')
    eff = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    r = c.post('/api/governance/activate', json={'artifact': 'kernel.params', 'semver': '2.0.0', 'effective_from': eff})
    assert r.status_code == 200 and r.get_json()['scheduled'] is True, r.get_json()
    a = r.get_json()
    monkeypatch.setenv('KERNEL_PARAMS', '2.0.0')
    governance.refresh()
    assert governance.artifact_semver('kernel.params') == '1.0.0'           # todavía no rige: el entorno no la adelanta
    monkeypatch.delenv('KERNEL_PARAMS')
    monkeypatch.setenv('GOV_RELEASE', a['release_hash'][:16])
    governance.refresh()
    assert governance.active().release_hash == boot
    monkeypatch.delenv('GOV_RELEASE')
    assert c.post('/api/governance/cancel', json={'decision_id': a['decision_id']}).status_code == 200
    for k, v in (('KERNEL_PARAMS', '2.0.0'), ('GOV_RELEASE', a['release_hash'][:16])):
        monkeypatch.setenv(k, v)
        governance.refresh()
        assert governance.artifact_semver('kernel.params') == '1.0.0' and governance.active().release_hash == boot, k
        monkeypatch.delenv(k)
    governance.refresh()


@needs_db
def test_programada_vencida_no_se_pisa_con_otra_activacion(db, monkeypatch):
    from sqlalchemy import text

    from core import governance, governance_flow, identity
    c = _client(monkeypatch)
    governance.refresh()
    governance_flow.validate(identity.operator(), 'kernel.params', '2.0.0')
    eff = (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat()
    r = c.post('/api/governance/activate', json={'artifact': 'kernel.params', 'semver': '2.0.0', 'effective_from': eff})
    assert r.status_code == 200 and r.get_json()['scheduled'] is True, r.get_json()
    sched = r.get_json()
    time.sleep(1.5)                                                     # vence; el reloj (60 s) todavía no corrió
    assert governance.artifact_semver('kernel.params') == '1.0.0'
    r = c.post('/api/governance/activate', json={'artifact': 'policy.gates', 'semver': '1.0.0', 'effective_from': 'now'})
    assert r.status_code == 200, r.get_json()
    assert governance.artifact_semver('kernel.params') == '2.0.0'       # la programada NO se perdió
    assert governance.artifact_semver('policy.gates') == '1.0.0'
    with db.connect() as cn:
        ap = cn.execute(text("SELECT status, output FROM decisions WHERE kind = 'governance.activate' "
                             "AND subject->>'applies' = :i"), {'i': sched['decision_id']}).all()
    assert len(ap) == 1 and ap[0].status == 'executed' and ap[0].output['in_force'] is True
    assert governance.refresh_job()['scheduled_applied'] == 0


@needs_db
def test_purga_no_vacia_lo_citado_hace_poco(db):
    from sqlalchemy import text

    from core import ai_calls, retention
    from core.decisions import canonical
    system = 'Eres Khipu chat (revisión batch G) …'
    b = canonical({'system': system})
    sha = hashlib.sha256(b).hexdigest()
    with db.begin() as c:
        c.execute(text("INSERT INTO decision_blobs (sha256, kind, body, size_bytes, retention_class, created_at) "
                       "VALUES (:s, 'ai_system', :b, :n, 'standard_90d', now() - interval '120 days') "
                       "ON CONFLICT DO NOTHING"), {'s': sha, 'b': zlib.compress(b), 'n': len(b)})
    rec = ai_calls.begin(system, '¿qué es NVDA?')
    ai_calls.finish(rec, text='respuesta', used='gemini:m', ok=True)
    ai_calls.submit(rec)
    ai_calls.flush()
    with db.connect() as c:
        assert c.execute(text('SELECT count(*) FROM ai_calls WHERE system_blob = :s'), {'s': sha}).scalar() == 1
    st = retention.status()
    assert st['pending'] == 0 and st['protected'] >= 1
    retention.purge()
    with db.connect() as c:
        assert c.execute(text('SELECT body IS NOT NULL FROM decision_blobs WHERE sha256 = :s'), {'s': sha}).scalar()
    with pytest.raises(Exception):                                     # la base tampoco lo deja vaciar a mano
        with db.begin() as c:
            c.execute(text("SELECT set_config('khipus.retention_job', 'on', true)"))
            c.execute(text('UPDATE decision_blobs SET body = NULL, purged_at = now(), '
                           'purge_decision_id = gen_random_uuid() WHERE sha256 = :s'), {'s': sha})


@needs_db
def test_caducar_propuestas_y_cuenta_de_la_casa_con_decision(db, monkeypatch):
    from sqlalchemy import text

    from brokerage import service as svc
    from ontology.db import session_scope

    def viol():
        with db.connect() as c:
            return c.execute(text('SELECT count(*) FROM kh_guard_violations')).scalar()
    with db.begin() as c:
        c.execute(text("SELECT set_config('khipus.decision_id', 'pytest', true)"))
        for oid in ('rvg-o1', 'rvg-o2'):
            c.execute(text("INSERT INTO broker_orders (id, client_id, symbol, side, order_type, status, source, "
                           "requires_approval, checks, expires_at, updated_at) VALUES (:i, 'house', 'NVDA', 'buy', "
                           "'market', 'pending_approval', 'mcp', true, '[]', now() - interval '1 hour', now())"),
                      {'i': oid})
        c.execute(text("INSERT INTO kh_guard_modes (mode) VALUES ('enforce')"))
    v0 = viol()
    try:
        with session_scope() as s:                       # GET /approvals: en enforce ya no falla
            assert svc.pending_approvals(s) == []
        with db.connect() as c:
            st = c.execute(text("SELECT status FROM broker_orders WHERE id IN ('rvg-o1', 'rvg-o2')")).all()
            dec = c.execute(text("SELECT status, subject FROM decisions WHERE kind = 'order.expire'")).all()
        assert {r[0] for r in st} == {'expired'}
        assert len(dec) == 1 and dec[0].status == 'expired' and dec[0].subject['n'] == 2
        # cuenta de la casa: cambiar ALPACA_BASE (papel → real) es un cambio de dinero → policy.change
        monkeypatch.setenv('ALPACA_KEY', 'PKTESTREVISIONG1')
        monkeypatch.setenv('ALPACA_SECRET', 'secret-revision-g')
        monkeypatch.setenv('ALPACA_BASE', 'https://paper-api.alpaca.markets')
        with session_scope() as s:
            svc.list_clients(s)
        monkeypatch.setenv('ALPACA_BASE', 'https://api.alpaca.markets')
        with session_scope() as s:
            rows = {c['id']: c for c in svc.list_clients(s)}
        assert rows[svc.HOUSE_ID]['mode'] == 'live'
        with db.connect() as c:
            pc = c.execute(text("SELECT principal_id, output FROM decisions WHERE kind = 'policy.change' "
                                "AND subject->>'policy' = 'broker.house_account'")).all()
        assert len(pc) == 1 and pc[0].principal_id == 'system:brokerage_house_account'
        assert pc[0].output['after']['mode'] == 'live' and pc[0].output['before']['mode'] == 'paper'
        assert viol() == v0
    finally:
        with db.begin() as c:
            c.execute(text("INSERT INTO kh_guard_modes (mode) VALUES ('warn')"))
