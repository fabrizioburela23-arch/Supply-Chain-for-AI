"""tests/test_ontology_agents.py — Fase 3: agentes que proponen, cola de
aprobación, brief matinal. Requiere Postgres real (DATABASE_URL).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres) configurada')


@pytest.fixture(scope='module')
def db():
    from ontology.db import init_schema, _get_engine, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()
    with session_scope() as s:
        # empresa de riesgo alto (China, sin margen -> concentración+market altos)
        apply_event(s, 'ObjectCreated', {
            'label': 'RiskCo', 'type': 'Company',
            'properties': {'country': 'China', 'margin': -0.5, 'mkt': 'RISKCO'},
        }, valid_from='2000-01-01', source='test', actor='pytest', object_id='RiskCo')
        # muchos proveedores para que el grado (chain risk) sume
        for i in range(6):
            sup_id = f'Sup{i}'
            apply_event(s, 'ObjectCreated', {'label': sup_id, 'type': 'Company', 'properties': {}},
                        valid_from='2000-01-01', source='test', actor='pytest', object_id=sup_id)
            apply_event(s, 'LinkCreated', {'rel_type': 'supply'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=sup_id, target_id='RiskCo')
        # empresa aislada (sin vínculos) para el Cartógrafo
        apply_event(s, 'ObjectCreated', {'label': 'Islote', 'type': 'Company', 'properties': {}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='Islote')
        # empresa segura (bajo riesgo) para contraste
        apply_event(s, 'ObjectCreated', {
            'label': 'SafeCo', 'type': 'Company', 'properties': {'country': 'EEUU', 'margin': 0.4},
        }, valid_from='2000-01-01', source='test', actor='pytest', object_id='SafeCo')
    yield
    Base.metadata.drop_all(engine)


def test_centinela_nrs_flags_high_risk_company(db):
    from ontology.db import session_scope
    from ontology.agents import CentinelaNRS, _compute_server_nrs
    from ontology.service import get_object

    with session_scope() as s:
        risk_score = _compute_server_nrs(s, get_object(s, 'RiskCo'))
        safe_score = _compute_server_nrs(s, get_object(s, 'SafeCo'))
        assert risk_score > safe_score
        assert risk_score >= CentinelaNRS.THRESHOLD


def test_cartografo_flags_isolated_object(db):
    from ontology.db import session_scope
    from ontology.agents import Cartografo

    with session_scope() as s:
        signals = Cartografo().observe(s)
        flagged_ids = {sig['company'].id for sig in signals}
        assert 'Islote' in flagged_ids
        assert 'RiskCo' not in flagged_ids  # tiene 6 proveedores, no está aislada


def test_run_agents_creates_proposals_and_dedupes(db):
    from ontology.db import session_scope
    from ontology.agents import run_agents
    from ontology.models import ProposedAction
    from sqlalchemy import select

    with session_scope() as s:
        summary1 = run_agents(s, only=['centinela_nrs', 'cartografo'])
        assert summary1['centinela_nrs']['ok']
        assert summary1['centinela_nrs']['proposals'] >= 1

    with session_scope() as s:
        n_after_first = s.query(ProposedAction).count()

    # segunda corrida inmediata: NO debe duplicar (dedupe por ventana de tiempo)
    with session_scope() as s:
        run_agents(s, only=['centinela_nrs', 'cartografo'])

    with session_scope() as s:
        n_after_second = s.query(ProposedAction).count()
        assert n_after_second == n_after_first  # sin duplicados


def test_approve_proposal_executes_action(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action
    from ontology.models import ProposedAction
    from ontology.service import get_object
    from sqlalchemy import select

    with session_scope() as s:
        pending = s.scalars(
            select(ProposedAction).where(ProposedAction.status == 'pending', ProposedAction.object_id == 'RiskCo')
        ).first()
        assert pending is not None
        payload = dict(pending.payload)
        result = execute_action(s, pending.action_type, payload, f'{pending.agent} → aprobado por tester')
        pending.status = 'approved'
        pending.resolved_by = 'tester'
        proposal_id = pending.id

    with session_scope() as s:
        obj = get_object(s, 'RiskCo')
        assert obj.properties.get('nrs_override') is not None
        p = s.get(ProposedAction, proposal_id)
        assert p.status == 'approved'
        assert p.resolved_by == 'tester'


def test_reject_proposal_does_not_execute(db):
    from ontology.db import session_scope
    from ontology.models import ProposedAction
    from sqlalchemy import select

    with session_scope() as s:
        pending = s.scalars(select(ProposedAction).where(ProposedAction.status == 'pending')).first()
        if pending is None:
            pytest.skip('no quedan propuestas pendientes para rechazar')
        pending.status = 'rejected'
        pending.resolved_by = 'tester'
        pid = pending.id

    with session_scope() as s:
        p = s.get(ProposedAction, pid)
        assert p.status == 'rejected'


def test_brief_matinal_reports_activity(db):
    from ontology.db import session_scope
    from ontology.agents import brief_matinal

    with session_scope() as s:
        brief = brief_matinal(s, hours=24)
        assert brief['actions_count'] >= 1  # la aprobación de arriba generó un ActionExecuted
        assert isinstance(brief['summary'], str) and brief['summary']


def test_agents_api_endpoints(db):
    import server
    os.environ.setdefault('SECRET_KEY', 'test')
    server.app.config['TESTING'] = True
    c = server.app.test_client()

    r = c.get('/api/ontology/agents/proposals?status=all')
    assert r.status_code == 200
    assert r.get_json()['count'] >= 1

    r2 = c.get('/api/ontology/agents/brief')
    assert r2.status_code == 200
    assert 'summary' in r2.get_json()

    # aprobar sin actor -> 400
    props = c.get('/api/ontology/agents/proposals?status=pending').get_json()['proposals']
    if props:
        r3 = c.post(f"/api/ontology/agents/proposals/{props[0]['id']}/approve", json={})
        assert r3.status_code == 400
