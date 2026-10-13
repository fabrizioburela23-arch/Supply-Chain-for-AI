"""tests/test_ledger_review_fixes.py — revisión de los pasos 18-21 (lote F): lo que los revisores encontraron en los
sitios del libro de decisiones y que aquí queda vigilado.

  · comité: el id de committee.run se RESERVA antes de la IA (sus filas de ai_calls lo citan) y, si el comité falla
    antes de guardar el memo, esa ficha existe igual como 'failed';
  · comité pedido por MCP: el hilo corre con el principal del token (mcp:<id>), no como system:committee;
  · aprobar un memo: si el libro falla → 503 ledger_unavailable; si ya salió una orden hacia Alpaca → 502
    unknown_state con su rastro durable (nunca un 500 genérico);
  · investigación: si el libro rechaza la ficha de UN analista, solo ese analista queda 'failed' (savepoint) y el
    job sigue (parcial), sin cancelar a los demás;
  · falsadores: si el libro rechaza un claim.status, se revierte solo esa falsación y la calificación del día queda;
  · alertas: un episodio largo deja una alert.fire cada FIRE_GAP_S (límite de ritmo), no solo la primera.
"""
import os
import sys
import threading
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
UTC = timezone.utc


@pytest.fixture(scope='module')
def db():
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    import brokerage.models  # noqa: F401
    import research.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    yield
    Base.metadata.drop_all(engine)


def _q(sql, **kw):
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        return [dict(r._mapping) for r in s.execute(text(sql), kw)]


def _fail_kind(monkeypatch, kind, when=lambda ctx: True):
    """El libro rechaza las fichas `kind` con un error REAL de Postgres (la transacción queda abortada)."""
    from sqlalchemy import text

    from core import decisions
    real = decisions._insert

    def bad(conn, ctx, *a, **k):
        if ctx.kind == kind and when(ctx):
            conn.execute(text('SELECT 1/0'))
        return real(conn, ctx, *a, **k)
    monkeypatch.setattr(decisions, '_insert', bad)


# ════════════════════════════════════════════════════════════════════════════
# alertas: límite de ritmo (sin base)
# ════════════════════════════════════════════════════════════════════════════
def test_alert_fire_una_ficha_cada_gap_mientras_la_condicion_sigue():
    from core import decision_sites as ds
    aid = str(uuid.uuid4())
    t0 = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
    prev, n = None, 0
    for minute in range(30):                           # sondeo cada minuto durante 30 min, condición siempre verdadera
        now = t0 + timedelta(minutes=minute)
        n += ds.alert_fire_due(aid, prev, now)
        prev = now                                     # last_fired_at se pisa en CADA sondeo
    assert n == 3                                      # minuto 0, 10 y 20 (antes: solo 1)
    # tras un reinicio (sin memoria) con el episodio en curso: no se repite enseguida, sí a los FIRE_GAP_S
    aid2 = str(uuid.uuid4())
    assert ds.alert_fire_due(aid2, t0 - timedelta(minutes=1), t0) is False
    assert ds.alert_fire_due(aid2, t0, t0 + timedelta(minutes=5)) is False
    assert ds.alert_fire_due(aid2, t0 + timedelta(minutes=5), t0 + timedelta(minutes=10)) is True
    # episodio nuevo tras una pausa larga: se escribe ya
    aid3 = str(uuid.uuid4())
    assert ds.alert_fire_due(aid3, t0 - timedelta(hours=2), t0) is True


# ════════════════════════════════════════════════════════════════════════════
# comité por MCP: principal del token en el hilo
# ════════════════════════════════════════════════════════════════════════════
def test_comite_por_mcp_corre_con_el_principal_del_token(monkeypatch):
    from contextlib import contextmanager

    from core import decision_sites as ds
    from core import identity
    import ontology.db as odb
    import research.committee as rc
    from mcp_server import tools as mt
    seen = {}

    @contextmanager
    def fake_scope():
        yield None

    def fake_run(s, eid, actor, client_id=None, memo_id=None):
        seen['p'] = ds.principal('committee', actor)
    monkeypatch.setattr(odb, 'session_scope', fake_scope)
    monkeypatch.setattr(rc, 'run_committee', fake_run)
    monkeypatch.setattr(rc, 'progress_clear', lambda mid: None)
    released = threading.Event()
    t = mt._run_committee_async('m-1', 'Nvidia', 'Claude', None, release=released.set,
                                who=identity.mcp('tok123', 'Claude'))
    t.join(5)
    assert seen['p'].id == 'mcp:tok123' and seen['p'].kind == 'external_ai' and released.is_set()


# ════════════════════════════════════════════════════════════════════════════
# aprobar un memo: fallos del libro con y sin orden enviada
# ════════════════════════════════════════════════════════════════════════════
def _decide_call(monkeypatch, fn, sent=()):
    from contextlib import contextmanager

    from flask import Flask

    from brokerage import service as bs
    from research import committee_api as ca

    @contextmanager
    def fake_scope():
        yield None
    monkeypatch.setattr(ca, 'ontology_available', lambda: True)
    monkeypatch.setattr(ca, '_pin_status', lambda: None)
    monkeypatch.setattr(ca, 'session_scope', fake_scope)
    trail = []
    monkeypatch.setattr(bs, 'record_unknown_after_send', lambda coids, actor, err, source='ui', client_id=None:
                        trail.append((list(coids), source, err)))

    def run(s, mid, actor, body):
        for c in sent:
            bs._SEND_TRACE.coids.append(c)            # como _send: la orden ya tocó Alpaca
        return fn()
    app = Flask('decide-test')
    with app.test_request_context('/api/committee/memo/m-1/approve', method='POST', json={'actor': 'Fabri'}):
        resp, code = ca._decide('m-1', run)
    return resp.get_json(), code, trail


def test_aprobar_memo_libro_caido_da_503(monkeypatch):
    from core.decisions import LedgerUnavailable

    def boom():
        raise LedgerUnavailable('no se pudo registrar la decisión (OperationalError)')
    body, code, trail = _decide_call(monkeypatch, boom)
    assert code == 503 and body['code'] == 'ledger_unavailable' and body['error_en'] and trail == []


def test_aprobar_memo_falla_tras_enviar_orden_da_estado_desconocido(monkeypatch):
    from core.decisions import LedgerUnavailable

    def boom():
        raise LedgerUnavailable('approval.grant no escrito')
    body, code, trail = _decide_call(monkeypatch, boom, sent=('kh-coid-1',))
    assert code == 502 and body['code'] == 'unknown_state' and body['client_order_id'] == 'kh-coid-1'
    assert trail == [(['kh-coid-1'], 'committee', 'LedgerUnavailable')]


# ════════════════════════════════════════════════════════════════════════════
# comité: id reservado (con base)
# ════════════════════════════════════════════════════════════════════════════
@needs_db
def test_committee_run_usa_el_id_reservado_antes_de_la_ia(db, monkeypatch):
    from core import decision_sites as ds
    from ontology.db import session_scope
    from research.committee import run_committee
    from research.llm import FakeProvider
    from tests.test_phase3 import DEPS, _FakeBroker, _chair_json, _fresh_entity_claims
    fixed = uuid.uuid4()
    monkeypatch.setattr(ds, 'reserve_id', lambda: fixed)
    with session_scope() as s:
        _fresh_entity_claims(s, 'Broadcom')
        m = run_committee(s, 'Broadcom', 'pytest', provider=FakeProvider([lambda p: _chair_json(p)]),
                          deps=dict(DEPS, brokerage=_FakeBroker()))
    rows = _q("SELECT id, kind, status FROM decisions WHERE id = CAST(:i AS uuid)", i=str(fixed))
    assert rows and rows[0]['kind'] == 'committee.run' and rows[0]['status'] == 'proposed'
    assert m['memo_id']


@needs_db
def test_comite_que_falla_tras_gastar_ia_deja_su_ficha_failed(db, monkeypatch):
    from core import ai, ai_calls
    from core import decision_sites as ds
    import research.committee as rc
    from ontology.db import session_scope
    from research.llm import CoreProvider
    fixed = uuid.uuid4()
    monkeypatch.setattr(ds, 'reserve_id', lambda: fixed)
    monkeypatch.setitem(ai._AI_PROVIDERS, 'claude', (lambda: True, lambda *a, **k: ('{"x": 1}', 'claude-fake')))
    monkeypatch.setattr(ai, 'circuit_open', lambda p: None)

    def boom(*a, **k):
        CoreProvider('claude').generate('sys', 'debate del comité', 800)       # la IA ya se pagó…
        raise RuntimeError('fallo después del debate')                         # …y el memo no se guarda
    monkeypatch.setattr(rc, '_run_committee', boom)
    with pytest.raises(RuntimeError), session_scope() as s:
        rc.run_committee(s, 'Broadcom', 'pytest')
    ai_calls.flush()
    rows = _q("SELECT kind, status, output FROM decisions WHERE id = CAST(:i AS uuid)", i=str(fixed))
    assert rows and rows[0]['kind'] == 'committee.run' and rows[0]['status'] == 'failed'
    calls = _q("SELECT decision_id, retention_class FROM ai_calls WHERE decision_id = CAST(:i AS uuid)", i=str(fixed))
    assert calls and all(c['retention_class'] == 'legal' for c in calls)


# ════════════════════════════════════════════════════════════════════════════
# investigación: el libro rechaza a UN analista
# ════════════════════════════════════════════════════════════════════════════
@needs_db
def test_libro_caido_para_un_analista_no_tumba_el_job(db, monkeypatch):
    from ontology.db import session_scope
    from research.models import AgentRun, ResearchClaim, ResearchJob
    from tests.test_research import _claim, _result, _run
    _fail_kind(monkeypatch, 'research.run', when=lambda ctx: ctx.subject.get('agent_type') == 'supply_chain')
    jid = _run('Intel', ['fundamental', 'supply_chain'],
               {'fundamental': [_result([_claim()])], 'supply_chain': [_result([_claim(topic='margins')])]})
    with session_scope() as s:
        j = s.get(ResearchJob, jid)
        runs = {r.agent_type: r for r in s.query(AgentRun).filter_by(job_id=jid)}
        assert j.status == 'partial' and 'supply_chain' in (j.error or '')
        assert runs['fundamental'].status == 'done'
        assert runs['supply_chain'].status == 'failed' and 'ledger_unavailable' in runs['supply_chain'].errors[0]
        assert {c.agent_type for c in s.query(ResearchClaim).filter_by(job_id=jid)} == {'fundamental'}
    st = {r['subject']['agent_type']: r['status'] for r in _q(
        "SELECT subject, status FROM decisions WHERE kind = 'research.run' AND subject->>'job_id' = :j", j=str(jid))}
    assert st == {'fundamental': 'executed'}          # el libro estaba "caído" solo para supply_chain
    closed = _q("SELECT output FROM decisions WHERE kind = 'research.job' AND subject->>'job_id' = :j "
                "ORDER BY seq", j=str(jid))
    assert closed[-1]['output']['job_status'] == 'partial'


# ════════════════════════════════════════════════════════════════════════════
# falsadores: el libro rechaza un claim.status
# ════════════════════════════════════════════════════════════════════════════
@needs_db
def test_falsador_con_libro_caido_no_pierde_la_calificacion_del_dia(db, monkeypatch):
    from ontology.db import session_scope
    from research.models import ClaimOutcome, ResearchClaim
    from research.outcomes import evaluate_due
    from tests.test_phase3 import _mk_claim, _series
    crash = {'MU': _series(date(2026, 5, 1), date(2027, 7, 1), lambda d: 100.0 if d < date(2026, 6, 20) else 60.0),
             'SPY': _series(date(2026, 5, 1), date(2027, 7, 1), lambda d: 500.0)}
    with session_scope() as s:
        c = _mk_claim(s, 'Micron', 'fundamental', 'positive', 'SHORT_TERM', 0.8)
        c.falsifier_rules = [{'metric': 'price', 'op': '<', 'threshold': 70, 'by': '2026-09-01'}]
        cid = c.id
        other = _mk_claim(s, 'Micron', 'technical', 'negative', 'SHORT_TERM', 0.7).id
    _fail_kind(monkeypatch, 'claim.status')
    with session_scope() as s:
        r = evaluate_due(s, now=datetime(2026, 6, 25, 12, tzinfo=UTC), price_fn=lambda sym, since: crash.get(sym))
    assert r['falsified'] == 0 and r['evaluated'] >= 1
    with session_scope() as s:
        assert s.get(ResearchClaim, cid).status == 'active'             # se reintenta en la próxima corrida
        graded = s.query(ClaimOutcome).filter(ClaimOutcome.claim_id.in_([cid, other])).all()
        assert graded and not [g for g in graded if g.checkpoint == 'falsifier']
        assert any(g.claim_id == other for g in graded)
