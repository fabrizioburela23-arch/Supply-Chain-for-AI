"""tests/test_repair_ontology.py — G2 (misión de reparación 2026-10-04): la
ontología se corrige SIN borrar nada.

  · G2a  un LinkCreated idéntico a una fila vigente no abre una segunda fila
         (el evento queda registrado como `dedup_of`; el replay lo ignora).
  · G2b  LinkRemoved DIRIGIDO (retracts_event_id) cierra SOLO la fila creada
         por ese evento — incluso para filas anteriores a G2 (sin event_id).
  · G2c  FusionarEntidad mueve los vínculos del alias al canónico conservando
         valid_from, retira el alias y la historia as_of sigue intacta.

Requiere Postgres real (DATABASE_URL) — se auto-saltan sin ella.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

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
        for oid in ('TSMC', 'NVDA', 'AMD', 'Luminar', 'Luminar_Lidar', 'Volvo'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company', 'properties': {}},
                        valid_from='2000-01-01', source='test', actor='pytest', object_id=oid)
    yield
    Base.metadata.drop_all(engine)


def _rows(s, src, tgt, rel='supply', vigentes=True):
    from sqlalchemy import select
    from ontology.models import LinkRecord
    q = select(LinkRecord).where(LinkRecord.source_id == src, LinkRecord.target_id == tgt, LinkRecord.rel_type == rel)
    if vigentes:
        q = q.where(LinkRecord.valid_to.is_(None))
    return s.scalars(q.order_by(LinkRecord.valid_from)).all()


def _replay(s, src, tgt, as_of=None):
    from ontology.service import as_of_graph
    g = as_of_graph(s, as_of)
    return [l for l in g['links'] if l['source'] == src and l['target'] == tgt]


# ───────────────────────── G2a · dedupe ─────────────────────────

def test_g2_link_created_repetido_no_duplica_fila(db):
    from ontology.db import session_scope
    from ontology.service import apply_event
    with session_scope() as s:
        e1 = apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 0.8, 'properties': {'headline': 'wafers'}},
                         valid_from='2020-01-01', source='test', actor='pytest', object_id='TSMC', target_id='NVDA')
        e1_id = str(e1.id)
    with session_scope() as s:
        e2 = apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 0.8, 'properties': {'headline': 'otra vez'}},
                         valid_from='2021-06-01', source='test', actor='pytest', object_id='TSMC', target_id='NVDA')
        assert e2.payload['properties'].get('dedup_of'), 'el evento repetido debe quedar marcado como dedup_of'
        assert e2.payload['properties'].get('dedup_event_id') == e1_id
    with session_scope() as s:
        rows = _rows(s, 'TSMC', 'NVDA')
        assert len(rows) == 1, 'un LinkCreated idéntico NO abre una segunda fila'
        assert str(rows[0].event_id) == e1_id
        assert len(_replay(s, 'TSMC', 'NVDA')) == 1, 'el replay desde eventos tampoco lo cuenta dos veces'
        # append-only: los DOS eventos quedan en la bitácora
        from sqlalchemy import select, func
        from ontology.models import Event
        n = s.scalar(select(func.count()).select_from(Event).where(Event.event_type == 'LinkCreated',
                                                                   Event.object_id == 'TSMC', Event.target_id == 'NVDA'))
        assert n == 2


def test_g2_peso_distinto_o_allow_duplicate_si_abre_fila(db):
    from ontology.db import session_scope
    from ontology.service import apply_event
    with session_scope() as s:
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 0.5},
                    valid_from='2022-01-01', source='test', actor='pytest', object_id='TSMC', target_id='NVDA')
    with session_scope() as s:
        assert len(_rows(s, 'TSMC', 'NVDA')) == 2, 'peso distinto = otra fila (no es duplicado exacto)'
    with session_scope() as s:
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 0.8, 'properties': {'allow_duplicate': True}},
                    valid_from='2023-01-01', source='test', actor='pytest', object_id='TSMC', target_id='NVDA')
    with session_scope() as s:
        assert len(_rows(s, 'TSMC', 'NVDA')) == 3, 'allow_duplicate desactiva el dedupe'
        assert len(_replay(s, 'TSMC', 'NVDA')) == 3


def test_g2_hecho_con_ventana_o_anterior_no_es_duplicado(db):
    """Un hecho con fecha de fin (Qualcomm→Huawei 2019-2021) o que empieza ANTES
    que la fila vigente aporta historia: no se deduplica."""
    from ontology.db import session_scope
    from ontology.service import apply_event
    with session_scope() as s:
        apply_event(s, 'LinkCreated', {'rel_type': 'license', 'weight': 1},
                    valid_from='2022-01-01', source='test', actor='pytest', object_id='AMD', target_id='NVDA')
    with session_scope() as s:
        e = apply_event(s, 'LinkCreated', {'rel_type': 'license', 'weight': 1},
                        valid_from='2019-01-01', valid_to='2021-01-01', source='test', actor='pytest',
                        object_id='AMD', target_id='NVDA')
        assert not (e.payload.get('properties') or {}).get('dedup_of')
        e2 = apply_event(s, 'LinkCreated', {'rel_type': 'license', 'weight': 1},
                         valid_from='2018-01-01', source='test', actor='pytest', object_id='AMD', target_id='NVDA')
        assert not (e2.payload.get('properties') or {}).get('dedup_of'), 'empieza antes: amplía la historia'
    with session_scope() as s:
        assert len(_rows(s, 'AMD', 'NVDA', rel='license', vigentes=False)) == 3
        assert len(_replay(s, 'AMD', 'NVDA', '2020-01-01')) == 2   # ventana 2019-21 + la de 2018


# ───────────────────────── G2b · retracción dirigida ─────────────────────────

def test_g2_retraccion_dirigida_cierra_solo_una_fila(db):
    """Dos filas vigentes del mismo par (pesos 0.5 y 0.8): retractar la de 0.5
    deja la de 0.8 — en tablas Y en el replay. RechazarVinculo/LinkRemoved sin
    dirección habría cerrado todas."""
    from ontology.db import session_scope
    from ontology.actions import execute_action
    with session_scope() as s:
        rows = _rows(s, 'TSMC', 'NVDA')
        victim = [r for r in rows if abs(float(r.weight) - 0.5) < 1e-9][0]
        victim_id, victim_ev = str(victim.id), str(victim.event_id)
        r = execute_action(s, 'RetractarVinculo', {'link_id': victim_id, 'razon': 'peso erróneo'}, actor='fabrizio')
        assert r['retracted_event_id'] == victim_ev
    with session_scope() as s:
        vig = _rows(s, 'TSMC', 'NVDA')
        assert len(vig) == 2 and all(abs(float(r.weight) - 0.8) < 1e-9 for r in vig)
        cerradas = [r for r in _rows(s, 'TSMC', 'NVDA', vigentes=False) if r.valid_to is not None]
        assert len(cerradas) == 1 and str(cerradas[0].id) == victim_id
        rep = _replay(s, 'TSMC', 'NVDA')
        assert len(rep) == 2 and all(abs(float(l['weight']) - 0.8) < 1e-9 for l in rep)
        # la retracción es una CORRECCIÓN: retroactiva en tiempo de validez (ni
        # ayer ni en 2022 se muestra la fila errónea)…
        ayer = datetime.now(timezone.utc) - timedelta(days=1)
        assert len(_replay(s, 'TSMC', 'NVDA', ayer)) == 2
        assert all(abs(float(l['weight']) - 0.5) > 1e-9 for l in _replay(s, 'TSMC', 'NVDA', '2022-06-01'))
        # …pero lo que se CREÍA queda en la bitácora (nada se borra)
        from sqlalchemy import select
        from ontology.models import Event
        assert s.get(Event, __import__('uuid').UUID(victim_ev)) is not None


def test_g2_retraccion_dirigida_en_filas_sin_event_id(db):
    """Filas anteriores a G2 (event_id NULL) — p. ej. las del snapshot migrado,
    donde el MISMO par tiene dos LinkCreated con el mismo valid_from GENESIS.
    Retractar una fila debe emparejarla con UN evento de creación y cerrar
    solo esa; la gemela queda viva en tablas y en el replay."""
    from sqlalchemy import select
    from ontology.db import session_scope
    from ontology.models import LinkRecord
    from ontology.service import apply_event, _creation_event_for
    from ontology.actions import execute_action
    genesis = '2015-01-01'
    with session_scope() as s:
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 0.6},
                    valid_from=genesis, source='migration', actor='script', object_id='TSMC', target_id='AMD')
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 0.6, 'properties': {'allow_duplicate': True}},
                    valid_from=genesis, source='migration', actor='script', object_id='TSMC', target_id='AMD')
    with session_scope() as s:           # simular filas heredadas: sin event_id
        for r in _rows(s, 'TSMC', 'AMD'):
            r.event_id = None
    with session_scope() as s:
        rows = _rows(s, 'TSMC', 'AMD')
        assert len(rows) == 2 and all(r.event_id is None for r in rows)
        ev_a = _creation_event_for(s, rows[0])
        assert ev_a is not None and ev_a.event_type == 'LinkCreated'
        victim_id = str(rows[0].id)
        execute_action(s, 'RetractarVinculo', {'link_id': victim_id, 'razon': 'duplicado de migración'}, actor='fabrizio')
    with session_scope() as s:
        vig = _rows(s, 'TSMC', 'AMD')
        assert len(vig) == 1 and str(vig[0].id) != victim_id
        assert len(_replay(s, 'TSMC', 'AMD')) == 1, 'el replay cierra exactamente la creación emparejada'
        # la segunda retracción (de la fila restante) sí vacía el par
        execute_action(s, 'RetractarVinculo', {'link_id': str(vig[0].id), 'razon': 'segunda'}, actor='fabrizio')
    with session_scope() as s:
        assert _rows(s, 'TSMC', 'AMD') == []
        assert _replay(s, 'TSMC', 'AMD') == []
        cerradas = s.scalars(select(LinkRecord).where(LinkRecord.source_id == 'TSMC', LinkRecord.target_id == 'AMD')).all()
        assert len(cerradas) == 2 and all(r.valid_to is not None and r.event_id is not None for r in cerradas)


def test_g2_retractar_vinculo_ya_cerrado_falla(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action, ActionError
    with session_scope() as s:
        cerrada = [r for r in _rows(s, 'TSMC', 'AMD', vigentes=False) if r.valid_to is not None][0]
        with pytest.raises(ActionError):
            execute_action(s, 'RetractarVinculo', {'link_id': str(cerrada.id), 'razon': 'x'}, actor='fabrizio')
        with pytest.raises(ActionError):
            execute_action(s, 'RetractarVinculo', {'link_id': 'no-es-uuid-valido', 'razon': 'x'}, actor='fabrizio')


# ───────────────────────── G2c · fusión de entidades ─────────────────────────

def test_g2_fusionar_entidad_mueve_links_y_conserva_historia(db):
    from ontology.db import session_scope
    from ontology.service import apply_event, get_object, object_links, as_of_graph
    from ontology.actions import execute_action, list_actions
    with session_scope() as s:
        # Luminar_Lidar (alias) provee a Volvo desde 2019; Luminar (canónico) ya provee a NVDA
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 0.7, 'properties': {'headline': 'lidar Volvo'}},
                    valid_from='2019-05-01', source='test', actor='pytest', object_id='Luminar_Lidar', target_id='Volvo')
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 0.3},
                    valid_from='2021-01-01', source='test', actor='pytest', object_id='Luminar', target_id='NVDA')
        # un vínculo alias → canónico (sería un bucle tras la fusión): debe desaparecer
        apply_event(s, 'LinkCreated', {'rel_type': 'partner', 'weight': 0.1},
                    valid_from='2020-01-01', source='test', actor='pytest', object_id='Luminar_Lidar', target_id='Luminar')
    with session_scope() as s:
        r = execute_action(s, 'FusionarEntidad', {'alias_id': 'Luminar_Lidar', 'canonical_id': 'Luminar',
                                                   'razon': 'misma empresa (Luminar Technologies)'}, actor='fabrizio')
        assert r['links_moved'] == 1 and r['links_dropped'] == 1
    with session_scope() as s:
        alias = get_object(s, 'Luminar_Lidar')
        assert alias is not None, 'nada se borra'
        assert alias.properties.get('retired') is True and alias.properties.get('merged_into') == 'Luminar'
        canon = get_object(s, 'Luminar')
        assert 'Luminar_Lidar' in (canon.properties.get('aliases') or [])
        assert object_links(s, 'Luminar_Lidar', direction='both') == [], 'el alias ya no tiene vínculos vigentes'
        moved = _rows(s, 'Luminar', 'Volvo')
        assert len(moved) == 1
        assert moved[0].valid_from.date().isoformat() == '2019-05-01', 'conserva la fecha original'
        assert abs(float(moved[0].weight) - 0.7) < 1e-9
        assert moved[0].properties.get('merged_from') == 'Luminar_Lidar'
        assert moved[0].properties.get('headline') == 'lidar Volvo'
        assert len(_rows(s, 'Luminar', 'NVDA')) == 1, 'el vínculo propio del canónico sigue igual'
        # hoy el replay ve Luminar→Volvo y nada del alias
        hoy = as_of_graph(s)['links']
        assert any(l['source'] == 'Luminar' and l['target'] == 'Volvo' for l in hoy)
        assert not any('Luminar_Lidar' in (l['source'], l['target']) for l in hoy)
        # en 2020 la empresa aparece UNA vez, con su nombre canónico y su fecha
        # real (la fusión corrige el pasado en tiempo de validez)…
        g2020 = as_of_graph(s, '2020-06-01')['links']
        assert any(l['source'] == 'Luminar' and l['target'] == 'Volvo' for l in g2020)
        assert not any('Luminar_Lidar' in (l['source'], l['target']) for l in g2020)
        assert not any(l['source'] == 'Luminar' and l['target'] == 'Volvo' for l in as_of_graph(s, '2019-01-01')['links'])
        # …y la bitácora conserva lo que se creía (los eventos del alias siguen ahí)
        from ontology.service import object_history
        assert any(e.event_type == 'LinkCreated' and e.object_id == 'Luminar_Lidar' for e in object_history(s, 'Luminar_Lidar'))
        # rastro auditable
        acts = [a for a in list_actions(s, action_type='FusionarEntidad')]
        assert acts and acts[0].actor == 'fabrizio' and acts[0].payload.get('links_moved') == 1


def test_g2_fusionar_entidad_mismo_objeto_o_inexistente_falla(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action, ActionError
    with session_scope() as s:
        with pytest.raises(ActionError):
            execute_action(s, 'FusionarEntidad', {'alias_id': 'NVDA', 'canonical_id': 'NVDA', 'razon': 'x'}, actor='f')
        with pytest.raises(ActionError):
            execute_action(s, 'FusionarEntidad', {'alias_id': 'NoExiste', 'canonical_id': 'NVDA', 'razon': 'x'}, actor='f')


def test_g2_catalogo_expone_las_dos_acciones(db):
    from ontology.actions import ACTION_CATALOG
    assert 'RetractarVinculo' in ACTION_CATALOG and 'FusionarEntidad' in ACTION_CATALOG
