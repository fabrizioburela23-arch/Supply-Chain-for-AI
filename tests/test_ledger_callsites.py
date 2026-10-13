"""tests/test_ledger_callsites.py — INFRA_OPERATIVA §2.5 (sitios de llamada del libro), parte DINERO (pasos 15-16).

Cada paso de una orden deja SU decisión, en la MISMA transacción que su efecto, encadenada por parent_id:
  order.preview (proposed | pending_approval | blocked) → [approval.grant | approval.deny] → order.confirm
  (approved | blocked | rejected | expired) → order.submit (executed; escrita ANTES de llamar a Alpaca) →
  decision_outcomes (order_status, fill) · order.cancel.
Un bloqueo deja su veredicto (run_checks = lo que rige) y sus violaciones; la puerta compilada (sombra) también.
Ninguna orden ejecutada lleva un veredicto 'block' (meta-puerta G8). Sin red, nunca una orden real.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

import requests  # noqa: E402

from tests.test_order_single_path import HTTPAlpaca  # noqa: E402

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PAPER = 'https://paper-api.alpaca.markets'


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


@pytest.fixture
def alpaca(monkeypatch, db):
    fake = HTTPAlpaca()
    for name in ('request', 'get', 'post', 'delete'):
        monkeypatch.setattr(requests, name, getattr(fake, name))
    for k, v in (('ALPACA_KEY', 'PKFAKEKEY0001'), ('ALPACA_SECRET', 'FAKE-SECRET-123'), ('ALPACA_BASE', PAPER)):
        monkeypatch.setenv(k, v)
    for k in ('BROKERAGE_TRADING_ENABLED', 'BROKERAGE_LIVE_ENABLED', 'BROKERAGE_AUTO_APPROVE_PAPER'):
        monkeypatch.delenv(k, raising=False)
    return fake


def _dec(did):
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        r = s.execute(text('SELECT id, kind, status, parent_id, principal_id, verdict, output, manifest FROM decisions '
                           'WHERE id = CAST(:i AS uuid)'), {'i': str(did)}).first()
        return dict(r._mapping) if r else None


def _children(did, kind=None):
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        rows = s.execute(text('SELECT id, kind, status, output FROM decisions WHERE parent_id = CAST(:i AS uuid) '
                              'ORDER BY seq'), {'i': str(did)}).all()
    return [dict(r._mapping) for r in rows if kind is None or r.kind == kind]


def _viols(did):
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        return [dict(r._mapping) for r in s.execute(text(
            'SELECT rule_iri, severity, value FROM decision_violations WHERE decision_id = CAST(:i AS uuid)'),
            {'i': str(did)})]


def test_submit_is_recorded_before_alpaca_is_called(alpaca, monkeypatch):
    from sqlalchemy import text
    from sqlalchemy.orm import object_session
    from ontology.db import session_scope
    from brokerage import service
    seen = {}
    orig = service._send

    def spy(alp, row):
        s = object_session(row)
        sid = (row.meta or {}).get('submit_decision_id')
        seen['submit_in_tx'] = s.execute(text("SELECT kind, status FROM decisions WHERE id = CAST(:i AS uuid)"),
                                         {'i': sid}).first()
        seen['confirm_in_tx'] = s.execute(text("SELECT status FROM decisions WHERE id = CAST(:i AS uuid)"),
                                          {'i': (row.meta or {}).get('confirm_decision_id')}).first()
        return orig(alp, row)
    monkeypatch.setattr(service, '_send', spy)
    with session_scope() as s:
        res = service.house_order(s, 'NVDA', 'buy', notional=15, requested_by='pytest')
    assert res['ok'], res
    assert tuple(seen['submit_in_tx']) == ('order.submit', 'executed')
    assert tuple(seen['confirm_in_tx']) == ('approved',)


def test_blocked_preview_records_the_enforced_verdict(alpaca):
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:                      # perfil estándar: US$6.000 > US$5.000 del moderado
        p = service.preview_order(s, 'house', 'AMD', 'buy', notional=6000, source='ui', requested_by='pytest')
    assert p['blocked'] and p['status'] == 'rejected'
    d = _dec(p['decision_id'])
    assert d['kind'] == 'order.preview' and d['status'] == 'blocked' and d['verdict']['outcome'] == 'block'
    v = _viols(p['decision_id'])
    enforced = [x for x in v if (x['value'] or {}).get('engine') == 'run_checks@1']
    assert any(x['rule_iri'] == 'khr:order.max_order_usd' and x['severity'] == 'block' for x in enforced), enforced
    assert any((x['value'] or {}).get('gate') == 'order.pre_trade' and x['severity'] == 'warn' for x in v)


def test_reject_and_cancel_and_refused_confirm(alpaca):
    from core import identity
    from ontology.db import session_scope
    from brokerage import service
    with identity.use(identity.mcp('tok9', 'Agente')):
        with session_scope() as s:
            p = service.preview_order(s, 'house', 'INTC', 'buy', notional=20, source='mcp', requested_by='mcp:tok9',
                                      rationale='prueba de rechazo')
        assert p['status'] == 'pending_approval'
        with session_scope() as s:                  # la IA no puede confirmarse a sí misma
            r = service.confirm_order(s, p['id'], 'mcp:tok9', source='mcp')
        assert r['code'] == 'requires_human_approval'
    cf = _children(p['decision_id'], 'order.confirm')
    assert cf and cf[-1]['status'] == 'rejected' and cf[-1]['output']['reason'] == 'requires_human_approval'
    with identity.use(identity.operator('ui')):
        with session_scope() as s:
            assert service.reject_preview(s, p['id'], 'op:fabrizio', reason='no ahora')['ok']
    deny = _children(p['decision_id'], 'approval.deny')
    assert deny and deny[0]['status'] == 'rejected'
    # orden enviada y luego cancelada → order.cancel hija de order.submit
    with session_scope() as s:
        res = service.house_order(s, 'ORCL', 'buy', notional=16, requested_by='pytest')
    oid, sub = res['order']['id'], res['decision_id']
    with session_scope() as s:
        c = service.cancel_order(s, oid, 'pytest')
    assert c['ok'], c
    cancels = _children(sub, 'order.cancel')
    assert cancels and cancels[0]['status'] == 'executed'


def test_no_executed_order_decision_carries_a_block(alpaca):
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        bad = s.execute(text("SELECT id FROM decisions WHERE kind LIKE 'order.%' AND status IN ('executed', 'approved') "
                             "AND verdict->>'outcome' = 'block'")).all()
        g8 = s.execute(text("SELECT count(*) FROM decision_violations WHERE rule_iri = "
                            "'khr:decision.money_executed_not_blocked'")).scalar()
    assert not bad and g8 == 0
