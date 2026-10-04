"""tests/test_repair_review2.py — G6b: segunda revisión adversarial (lente
"contratos y operación") sobre G6/O1/O2. Cada test reproduce un hallazgo."""
import io
import json
import logging
import os
import sys
from collections import namedtuple

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL')

C = namedtuple('C', 'subject_entity_id agent_type topic horizon id')


def test_g6b_el_comite_no_cuenta_dos_veces_una_conclusion_vieja():
    from research.committee import _prefer_canonical
    claims = [C('Eaton', 'fundamental', 'margins', 'SHORT_TERM', 1), C('EatonCorp', 'fundamental', 'margins', 'SHORT_TERM', 2),
              C('EatonCorp', 'news', 'demand', 'SHORT_TERM', 3)]
    kept = {c.id for c in _prefer_canonical(claims, 'Eaton')}
    assert kept == {1, 3}            # la vieja del mismo agente/tema/horizonte se ignora; la única de 'news' se ve


@needs_db
def test_g6b_guardian_de_cifras_revisa_ids_viejos():
    from datetime import datetime, timezone
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    import research.models as RM
    from research.runner import retract_unsupported
    from core.entities import entity_ids_for
    eng = _get_engine(); Base.metadata.drop_all(eng); init_schema(retries=1)
    try:
        alias = next(a for a in entity_ids_for('SouthernCo') if a != 'SouthernCo')
        with session_scope() as s:
            s.add(RM.ResearchClaim(id='c-old', agent_id='a', agent_type='fundamental', agent_version='1',
                                   subject_entity_id=alias, predicate='P', claim_type='observation', topic='margins',
                                   stance='positive', statement_es='Ingresos de $350B el próximo año', horizon='SHORT_TERM',
                                   depth='QUICK', valid_from=datetime.now(timezone.utc), confidence=0.5))
        with session_scope() as s:
            assert retract_unsupported(s, 'SouthernCo') == 1
        with session_scope() as s:
            assert s.get(RM.ResearchClaim, 'c-old').status == 'retracted'
    finally:
        Base.metadata.drop_all(eng)


def test_g6b_chat_ve_clientes_en_get_supply_chain():
    from core import khipu_chat as K
    from mcp_server import tools as T
    from mcp_server.auth import Principal
    ctx = T.Ctx(principal=Principal(token_id='x', name='t', scopes=frozenset({'read'})))
    for nid in ('TSMC', 'Nvidia'):
        r = T.call('get_supply_chain', {'id': nid}, ctx)
        d = json.loads(K._fmt_result(r))
        e = [x for x in d['edges'] if isinstance(x, dict)]
        assert sum(1 for x in e if x['source'] == nid) >= 5 and sum(1 for x in e if x['target'] == nid) >= 5
        assert d['counts'] == r['counts']                    # el total real sigue a la vista


def test_g6b_confirmado_libera_aunque_haya_confianza_heredada():
    from matrix.engine import link_confidence
    assert link_confidence({'confidence': 0.3, 'rel_label': 'Posible…', 'status': 'confirmed'}) is None


@needs_db
def test_g6b_confirmacion_llega_al_replay():
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base, LinkRecord
    from ontology.service import apply_event, as_of_graph
    from ontology.actions import execute_action
    eng = _get_engine(); Base.metadata.drop_all(eng); init_schema(retries=1)
    try:
        with session_scope() as s:
            for i in ('X', 'TSMC'):
                apply_event(s, 'ObjectCreated', {'label': i, 'type': 'Company'}, valid_from='2000-01-01',
                            source='t', actor='t', object_id=i)
            apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 2,
                                           'properties': {'rel_label': 'Posible proveedor de gases'}},
                        valid_from='2000-01-01', source='t', actor='t', object_id='X', target_id='TSMC')
        with session_scope() as s:
            lid = str(s.query(LinkRecord).first().id)
            execute_action(s, 'ConfirmarVinculo', {'link_id': lid}, actor='fabrizio')
        with session_scope() as s:
            row = next(l for l in as_of_graph(s)['links'] if l['source'] == 'X')
            assert row['properties'].get('status') == 'confirmed'
    finally:
        Base.metadata.drop_all(eng)


def test_g6b_sin_log_json_no_se_leen_atributos_del_job(monkeypatch):
    """Con LOG_JSON apagado, el `finally` de execute_job no toca job.status/job.error
    (tras un fallo de flush eso lanzaba otra excepción y tapaba la causa real)."""
    from research import runner
    monkeypatch.delenv('LOG_JSON', raising=False)

    class Boom:
        id, entity_id, depth, requested_by, trigger = 'j', 'E', 'QUICK', None, {}

        @property
        def status(self):
            raise RuntimeError('PendingRollbackError simulado')
        error = status
    monkeypatch.setattr(runner, '_execute_job', lambda *a, **k: (_ for _ in ()).throw(ValueError('causa real')))
    with pytest.raises(ValueError, match='causa real'):
        runner.execute_job(None, Boom())


def test_g6b_mcp_declara_ownership():
    from mcp_server import tools as T
    from mcp_server.auth import Principal
    ctx = T.Ctx(principal=Principal(token_id='x', name='t', scopes=frozenset({'read'})))
    r = T.call('get_supply_chain', {'id': 'Intel'}, ctx)
    assert 'ownership' in r['edge_semantics']['relation_class']
    c = T.call('get_company', {'id_or_ticker': 'Intel', 'include_live': False}, ctx)
    assert 'ownership' in c['edge_semantics']['relation_class']


@needs_db
def test_g6b_pin_malo_no_gasta_el_cupo_ni_recibe_plan_viejo(monkeypatch):
    import server
    from core import pin
    from core import http as _h
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    eng = _get_engine(); Base.metadata.drop_all(eng); init_schema(retries=1)
    try:
        pin._reset_for_tests(); _h._rate_buckets.clear()
        monkeypatch.setenv('TRADE_PIN', 'pin-g6b-8642')
        c = server.app.test_client()
        assert c.get('/api/ontology/reconcile/plan?summary=1&fresh=1', headers={'X-Trade-Pin': 'malo'}).status_code == 401
        pin._reset_for_tests()
        for _ in range(6):                       # PIN malo varias veces (sin llegar al bloqueo)
            c.post('/api/ontology/reconcile/rollback', json={'actor': 'a', 'run_id': 'r'}, headers={'X-Trade-Pin': 'malo'})
            pin._reset_for_tests()
        r = c.post('/api/ontology/reconcile/rollback', json={'actor': 'a', 'run_id': 'r', 'confirm_db': 'x'},
                   headers={'X-Trade-Pin': 'pin-g6b-8642'})
        assert r.status_code != 429, 'el cupo no debe gastarse con PIN malo'
    finally:
        Base.metadata.drop_all(eng)


@needs_db
def test_g6c_propuesta_no_se_deduplica_contra_un_hecho_existente():
    """Una propuesta sin peso sobre un par con un hecho vigente sin peso: antes el
    dedupe la convertía en no-op y devolvía el link_id del HECHO (aprobar/rechazar
    la propuesta actuaba sobre él)."""
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base, LinkRecord
    from ontology.service import apply_event
    from ontology.actions import execute_action
    eng = _get_engine(); Base.metadata.drop_all(eng); init_schema(retries=1)
    try:
        with session_scope() as s:
            for i in ('X', 'Y'):
                apply_event(s, 'ObjectCreated', {'label': i, 'type': 'Company'}, valid_from='2000-01-01',
                            source='t', actor='t', object_id=i)
            apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'properties': {'headline': 'hecho 2021'}},
                        valid_from='2021-01-01', source='migration_v0_temporal', actor='t', object_id='X', target_id='Y')
        with session_scope() as s:
            fact_id = str(s.query(LinkRecord).first().id)
            r = execute_action(s, 'ProponerVinculo', {'from_id': 'X', 'to_id': 'Y', 'tipo': 'supply', 'fuente': 'agente'},
                               actor='agente')
            assert r['link_id'] and r['link_id'] != fact_id
        with session_scope() as s:
            assert s.query(LinkRecord).filter(LinkRecord.valid_to.is_(None)).count() == 2
    finally:
        Base.metadata.drop_all(eng)
