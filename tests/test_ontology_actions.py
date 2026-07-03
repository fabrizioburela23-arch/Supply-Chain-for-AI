"""tests/test_ontology_actions.py — Fase 2: catálogo de Acciones (escritura
humana auditada). Requiere Postgres real (DATABASE_URL) — se auto-saltan si
no está configurada, igual que test_ontology.py.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres) configurada')


@pytest.fixture(scope='module')
def db():
    from ontology.db import init_schema, _get_engine
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()
    # semilla mínima: dos empresas para que las Acciones tengan sobre qué operar
    from ontology.db import session_scope
    from ontology.service import apply_event
    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': 'ACME', 'type': 'Company', 'properties': {'mkt': 'ACME', 'country': 'EEUU'}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='ACME')
        apply_event(s, 'ObjectCreated', {'label': 'Widgetco', 'type': 'Company', 'properties': {}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='Widgetco')
    yield
    Base.metadata.drop_all(engine)


def test_crear_tesis(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action
    from ontology.service import get_object, object_links

    with session_scope() as s:
        r = execute_action(s, 'CrearTesis',
                            {'company_id': 'ACME', 'stance': 'long', 'confidence': 0.75, 'rationale': 'moat fuerte'},
                            actor='ana')
        thesis_id = r['thesis_id']
    with session_scope() as s:
        thesis = get_object(s, thesis_id)
        assert thesis.type == 'Thesis'
        assert thesis.properties['stance'] == 'long'
        assert thesis.properties['author'] == 'ana'
        links = object_links(s, thesis_id, direction='out')
        assert any(l.target_id == 'ACME' and l.rel_type == 'about' for l in links)


def test_crear_tesis_rejects_invalid_stance(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action, ActionError

    with session_scope() as s:
        with pytest.raises(ActionError):
            execute_action(s, 'CrearTesis',
                            {'company_id': 'ACME', 'stance': 'moon', 'confidence': 0.5, 'rationale': 'x'},
                            actor='ana')


def test_action_requires_actor(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action, ActionError

    with session_scope() as s:
        with pytest.raises(ActionError):
            execute_action(s, 'AnotarObjeto', {'object_id': 'ACME', 'texto': 'nota'}, actor=None)


def test_action_on_unknown_object_fails(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action, ActionError

    with session_scope() as s:
        with pytest.raises(ActionError):
            execute_action(s, 'AnotarObjeto', {'object_id': 'NoExiste123', 'texto': 'nota'}, actor='ana')


def test_marcar_riesgo_updates_object(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action
    from ontology.service import get_object

    with session_scope() as s:
        execute_action(s, 'MarcarRiesgo', {'company_id': 'ACME', 'nivel': 80, 'razon': 'sanción reciente'}, actor='ana')
    with session_scope() as s:
        obj = get_object(s, 'ACME')
        assert obj.properties['nrs_override'] == 80
        assert obj.properties['nrs_override_reason'] == 'sanción reciente'


def test_proponer_confirmar_vinculo(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action
    from ontology.models import LinkRecord
    import uuid

    with session_scope() as s:
        r = execute_action(s, 'ProponerVinculo',
                            {'from_id': 'ACME', 'to_id': 'Widgetco', 'tipo': 'partner', 'metadata': {}, 'fuente': 'analista'},
                            actor='ana')
        link_id = r['link_id']
        assert r['status'] == 'proposed'

    with session_scope() as s:
        link = s.get(LinkRecord, uuid.UUID(link_id))
        assert link.properties['status'] == 'proposed'

    with session_scope() as s:
        execute_action(s, 'ConfirmarVinculo', {'link_id': link_id}, actor='beto')

    with session_scope() as s:
        link = s.get(LinkRecord, uuid.UUID(link_id))
        assert link.properties['status'] == 'confirmed'
        assert link.properties['confirmed_by'] == 'beto'
        assert link.valid_to is None  # sigue vigente


def test_rechazar_vinculo_closes_interval(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action
    from ontology.models import LinkRecord
    import uuid

    with session_scope() as s:
        r = execute_action(s, 'ProponerVinculo',
                            {'from_id': 'Widgetco', 'to_id': 'ACME', 'tipo': 'compite', 'metadata': {}, 'fuente': 'x'},
                            actor='ana')
        link_id = r['link_id']

    with session_scope() as s:
        execute_action(s, 'RechazarVinculo', {'link_id': link_id}, actor='beto')

    with session_scope() as s:
        link = s.get(LinkRecord, uuid.UUID(link_id))
        assert link.properties['status'] == 'rejected'
        assert link.valid_to is not None  # ya no vigente


def test_registrar_decision_and_ajustar_posicion(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action
    from ontology.service import get_object

    with session_scope() as s:
        r = execute_action(s, 'RegistrarDecision',
                            {'decision': 'reducir exposición 20%', 'company_id': 'ACME',
                             'contexto': {'origin': 'stress_test', 'affected_count': 5}},
                            actor='ana')
        decision_id = r['decision_id']

    with session_scope() as s:
        r2 = execute_action(s, 'AjustarPosicion',
                             {'ticker': 'ACME', 'delta': -5, 'razon': 'seguimiento de la decisión',
                              'decision_id': decision_id}, actor='ana')
        assert r2['company_id'] == 'ACME'  # resuelto por properties.mkt

    with session_scope() as s:
        adj = get_object(s, r2['adjustment_id'])
        assert adj.properties['decision_id'] == decision_id
        assert adj.properties['delta'] == -5


def test_corregir_dato_tracks_before_and_after(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action, list_actions
    from ontology.service import get_object

    with session_scope() as s:
        r = execute_action(s, 'CorregirDato',
                            {'object_id': 'ACME', 'campo': 'preipo', 'valor_nuevo': False, 'fuente': 'confirmado en 10-K'},
                            actor='ana')
        assert r['valor_nuevo'] is False

    with session_scope() as s:
        obj = get_object(s, 'ACME')
        assert obj.properties['preipo'] is False
        acts = list_actions(s, object_id='ACME', action_type='CorregirDato')
        assert len(acts) == 1
        assert acts[0].payload['fuente'] == 'confirmado en 10-K'


def test_list_actions_is_filterable_and_ordered(db):
    from ontology.db import session_scope
    from ontology.actions import list_actions

    with session_scope() as s:
        all_acme = list_actions(s, object_id='ACME')
        assert len(all_acme) >= 4  # tesis, riesgo, decisión, corrección de los tests anteriores
        recorded = [a.recorded_at for a in all_acme]
        assert recorded == sorted(recorded, reverse=True)  # más reciente primero

        only_ana = list_actions(s, actor='ana')
        only_beto = list_actions(s, actor='beto')
        assert all(a.actor == 'ana' for a in only_ana)
        assert all(a.actor == 'beto' for a in only_beto)
        assert len(only_beto) >= 1  # ConfirmarVinculo/RechazarVinculo se ejecutaron como 'beto'
        assert len(only_ana) >= 1
