"""tests/test_ops_link_status_event.py — INFRA_OPERATIVA paso 3: ConfirmarVinculo / RechazarVinculo emiten
`LinkStatusChanged` en vez de mutar link.properties a mano (W5, GV-02).

Garantiza:
  · confirmar deja un evento LinkStatusChanged {status, link_id, creation_event_id, by} y la fila queda
    confirmed (la fila es una proyección del registro); el ActionExecuted apunta al evento (status_event_id);
  · el replay (as_of) REPRODUCE el estado desde el registro, y por su fecha: en una foto anterior a la
    confirmación el vínculo no aparece confirmado (antes "filtraba el futuro");
  · rechazar: estado rejected + intervalo cerrado, en tablas y en el replay;
  · el descuento de "no verificado" desaparece de las matrices al confirmar (efecto económico real);
  · el handler ya no asigna link.properties (prueba estática) y un status inválido se rechaza.
"""
import os
import sys
import time
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


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
        for oid in ('LS_A', 'LS_B', 'LS_C'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=oid)
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 4.0,
                                       'properties': {'rel_label': 'Posible proveedor de gases'}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='LS_A', target_id='LS_B')
        apply_event(s, 'LinkCreated', {'rel_type': 'fab', 'weight': 3.0, 'properties': {}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='LS_C', target_id='LS_B')
    yield engine
    Base.metadata.drop_all(engine)


def _link(s, src, tgt):
    from ontology.models import LinkRecord
    return s.query(LinkRecord).filter_by(source_id=src, target_id=tgt).first()


@needs_db
def test_confirmar_emite_link_status_changed_y_el_replay_lo_reproduce_por_fecha(db):
    from matrix.engine import build_matrices
    from ontology.actions import execute_action
    from ontology.db import session_scope
    from ontology.models import Event
    from ontology.service import as_of_graph
    with session_scope() as s:
        lk = _link(s, 'LS_A', 'LS_B')
        lid, cid = str(lk.id), str(lk.event_id)
        mats, idx, _ = build_matrices(s)
        w_before = float(mats['supply'][idx['LS_A'], idx['LS_B']])
    antes = time.time()
    time.sleep(0.05)
    with session_scope() as s:
        r = execute_action(s, 'ConfirmarVinculo', {'link_id': lid}, actor='fabrizio')
    with session_scope() as s:
        ev = s.query(Event).filter_by(event_type='LinkStatusChanged').order_by(Event.recorded_at.desc()).first()
        assert ev is not None and str(ev.id) == r['status_event_id']
        assert ev.payload == {'status': 'confirmed', 'link_id': lid, 'rel_type': 'supply',
                              'creation_event_id': cid, 'by': 'fabrizio'}
        act = s.query(Event).filter(Event.event_type == 'ActionExecuted',
                                    Event.payload['action'].astext == 'ConfirmarVinculo').first()
        assert act.payload['status_event_id'] == str(ev.id) and act.payload['creation_event_id'] == cid
        row = _link(s, 'LS_A', 'LS_B')
        assert row.properties['status'] == 'confirmed' and row.properties['confirmed_by'] == 'fabrizio'
        # replay de "ahora" = tabla materializada
        rep = next(l for l in as_of_graph(s)['links'] if l['event_id'] == cid)
        assert rep['properties']['status'] == 'confirmed' and rep['properties']['confirmed_by'] == 'fabrizio'
        # foto ANTERIOR a la confirmación: todavía no estaba confirmado
        from datetime import datetime, timezone
        past = datetime.fromtimestamp(antes, tz=timezone.utc)
        old = next(l for l in as_of_graph(s, past)['links'] if l['event_id'] == cid)
        assert old['properties'].get('status') != 'confirmed'
        # efecto económico: "posible" pesaba 0,3×; confirmado, el peso completo
        mats, idx, _ = build_matrices(s)
        w_after = float(mats['supply'][idx['LS_A'], idx['LS_B']])
    assert w_before == pytest.approx(4.0 * 0.3) and w_after == pytest.approx(4.0)


@needs_db
def test_rechazar_emite_estado_y_cierra_el_intervalo_en_tablas_y_replay(db):
    from ontology.actions import execute_action
    from ontology.db import session_scope
    from ontology.models import Event, LinkRecord
    from ontology.service import as_of_graph
    with session_scope() as s:
        lk = _link(s, 'LS_C', 'LS_B')
        lid, cid = str(lk.id), str(lk.event_id)
    with session_scope() as s:
        execute_action(s, 'RechazarVinculo', {'link_id': lid}, actor='beto')
    with session_scope() as s:
        row = s.get(LinkRecord, uuid.UUID(lid))
        assert row.properties['status'] == 'rejected' and row.properties['rejected_by'] == 'beto'
        assert row.valid_to is not None
        st = s.query(Event).filter(Event.event_type == 'LinkStatusChanged',
                                   Event.payload['creation_event_id'].astext == cid).one()
        assert st.payload['status'] == 'rejected'
        assert not any(l['event_id'] == cid for l in as_of_graph(s)['links'])


@needs_db
def test_status_invalido_se_rechaza(db):
    from ontology.db import session_scope
    from ontology.service import OntologyError, apply_event
    with pytest.raises(OntologyError):
        with session_scope() as s:
            lk = _link(s, 'LS_A', 'LS_B')
            apply_event(s, 'LinkStatusChanged', {'status': 'aprobadísimo', 'link_id': str(lk.id)},
                        valid_from='2026-01-01', source='test', actor='pytest',
                        object_id='LS_A', target_id='LS_B')


def test_el_handler_ya_no_muta_link_properties():
    src = open(os.path.join(ROOT, 'ontology', 'actions.py'), encoding='utf-8').read()
    body = src[src.index('def _resolver_vinculo'):src.index('def _link_by_id')]
    assert 'link.properties =' not in body and "'LinkStatusChanged'" in body
    from ontology.models import EventType
    assert EventType.LINK_STATUS_CHANGED.value == 'LinkStatusChanged'
