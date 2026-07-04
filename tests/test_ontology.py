"""tests/test_ontology.py — Fase 1: esquema de eventos, materialización,
time-travel (as_of) y diff. Requiere una Postgres real accesible vía
DATABASE_URL (se skippean automáticamente si no está configurada — no
bloquean CI sin base de datos, igual que los tests que necesitan API keys).

Ejecutar con una Postgres de prueba:
    export DATABASE_URL=postgresql://user:pass@localhost:5432/khipus_test
    pytest tests/test_ontology.py -v
"""
import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres) configurada')


@pytest.fixture(scope='module')
def db():
    from ontology.db import init_schema, _get_engine
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)  # tablas limpias para esta suite
    init_schema()
    yield
    Base.metadata.drop_all(engine)  # limpieza al final


def test_apply_event_creates_object(db):
    from ontology.db import session_scope
    from ontology.service import apply_event, get_object

    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': 'ACME', 'type': 'Company', 'properties': {'ticker': 'ACME'}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='ACME')
    with session_scope() as s:
        obj = get_object(s, 'ACME')
        assert obj is not None
        assert obj.label == 'ACME'
        assert obj.properties.get('ticker') == 'ACME'


def test_object_updated_merges_properties(db):
    from ontology.db import session_scope
    from ontology.service import apply_event, get_object

    with session_scope() as s:
        apply_event(s, 'ObjectUpdated', {'properties': {'margin': 0.4}},
                    valid_from='2024-01-01', source='test', actor='pytest', object_id='ACME')
    with session_scope() as s:
        obj = get_object(s, 'ACME')
        assert obj.properties.get('ticker') == 'ACME'  # el campo viejo se conserva
        assert obj.properties.get('margin') == 0.4      # el nuevo se añade


def test_link_created_and_visible_now(db):
    from ontology.db import session_scope
    from ontology.service import apply_event, object_links

    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': 'Supplier', 'type': 'Company'},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='Supplier')
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 5},
                    valid_from='2020-01-01', source='test', actor='pytest',
                    object_id='Supplier', target_id='ACME')
    with session_scope() as s:
        links = object_links(s, 'Supplier', direction='out')
        assert len(links) == 1
        assert links[0].target_id == 'ACME'


def test_time_travel_before_and_after_link(db):
    """Criterio de aceptación del roadmap: as_of devuelve estados coherentes."""
    from ontology.db import session_scope
    from ontology.service import as_of_graph, _parse_dt

    with session_scope() as s:
        before = as_of_graph(s, _parse_dt('2010-01-01'))   # antes del LinkCreated (2020)
        after = as_of_graph(s, _parse_dt('2021-01-01'))    # después

    before_pairs = {(l['source'], l['target']) for l in before['links']}
    after_pairs = {(l['source'], l['target']) for l in after['links']}
    assert ('Supplier', 'ACME') not in before_pairs
    assert ('Supplier', 'ACME') in after_pairs


def test_link_removed_closes_interval(db):
    from ontology.db import session_scope
    from ontology.service import apply_event, as_of_graph, _parse_dt

    with session_scope() as s:
        apply_event(s, 'LinkRemoved', {'rel_type': 'supply'},
                    valid_from='2022-06-01', source='test', actor='pytest',
                    object_id='Supplier', target_id='ACME')
    with session_scope() as s:
        still_active = as_of_graph(s, _parse_dt('2021-06-01'))
        after_removal = as_of_graph(s, _parse_dt('2023-01-01'))

    active_pairs = {(l['source'], l['target']) for l in still_active['links']}
    removed_pairs = {(l['source'], l['target']) for l in after_removal['links']}
    assert ('Supplier', 'ACME') in active_pairs
    assert ('Supplier', 'ACME') not in removed_pairs


def test_wildcard_removal_matches_replay(db):
    """Regresión: un LinkRemoved SIN rel_type cierra todos los rel del par en la
    tabla materializada — el replay (as_of) debe hacer LO MISMO. Antes el replay
    indexaba la remoción por (s,t,None) y nunca casaba, divergiendo de tablas."""
    from ontology.db import session_scope
    from ontology.service import apply_event, as_of_graph, _parse_dt
    from ontology.models import LinkRecord

    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': 'W1', 'type': 'Company'},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='W1')
        apply_event(s, 'ObjectCreated', {'label': 'W2', 'type': 'Company'},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='W2')
        apply_event(s, 'LinkCreated', {'rel_type': 'supply'},
                    valid_from='2020-01-01', source='test', actor='pytest',
                    object_id='W1', target_id='W2')
        apply_event(s, 'LinkRemoved', {},  # sin rel_type: comodín
                    valid_from='2022-01-01', source='test', actor='pytest',
                    object_id='W1', target_id='W2')
    with session_scope() as s:
        replay_pairs = {(l['source'], l['target'])
                        for l in as_of_graph(s, _parse_dt('2023-01-01'))['links']}
        live_rows = s.query(LinkRecord).filter(
            LinkRecord.source_id == 'W1', LinkRecord.target_id == 'W2',
            LinkRecord.valid_to.is_(None)).count()
    assert ('W1', 'W2') not in replay_pairs   # el replay también lo ve cerrado
    assert live_rows == 0                     # y la tabla materializada igual


def test_recreated_link_after_removal_is_active(db):
    """Regresión: una remoción solo mata creaciones ANTERIORES. Si el vínculo se
    re-crea después de removido, vuelve a estar vigente (antes el replay lo
    mataba para siempre con cualquier remoción pasada)."""
    from ontology.db import session_scope
    from ontology.service import apply_event, as_of_graph, _parse_dt

    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': 'R1', 'type': 'Company'},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='R1')
        apply_event(s, 'ObjectCreated', {'label': 'R2', 'type': 'Company'},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='R2')
        apply_event(s, 'LinkCreated', {'rel_type': 'supply'}, valid_from='2018-01-01',
                    source='test', actor='pytest', object_id='R1', target_id='R2')
        apply_event(s, 'LinkRemoved', {'rel_type': 'supply'}, valid_from='2019-01-01',
                    source='test', actor='pytest', object_id='R1', target_id='R2')
        apply_event(s, 'LinkCreated', {'rel_type': 'supply'}, valid_from='2021-01-01',
                    source='test', actor='pytest', object_id='R1', target_id='R2')
    with session_scope() as s:
        during_gap = {(l['source'], l['target'])
                      for l in as_of_graph(s, _parse_dt('2020-01-01'))['links']}
        after_recreate = {(l['source'], l['target'])
                          for l in as_of_graph(s, _parse_dt('2022-01-01'))['links']}
    assert ('R1', 'R2') not in during_gap
    assert ('R1', 'R2') in after_recreate


def test_rejected_link_replay_isomorphic(db):
    """Regresión Fase 2: RechazarVinculo debe emitir LinkRemoved (evento), no
    solo mutar la tabla. El replay as_of(hoy) y la tabla materializada tienen
    que contar la MISMA historia tras el rechazo."""
    from ontology.db import session_scope
    from ontology.actions import execute_action
    from ontology.service import apply_event, as_of_graph
    from ontology.models import LinkRecord

    with session_scope() as s:
        for oid in ('P1', 'P2'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company'},
                        valid_from='2000-01-01', source='test', actor='pytest', object_id=oid)
        r = execute_action(s, 'ProponerVinculo',
                            {'from_id': 'P1', 'to_id': 'P2', 'tipo': 'supply'}, actor='ana')
        link_id = r['link_id']
    with session_scope() as s:
        execute_action(s, 'RechazarVinculo', {'link_id': link_id}, actor='bob')
    with session_scope() as s:
        replay_pairs = {(l['source'], l['target']) for l in as_of_graph(s)['links']}
        live_rows = s.query(LinkRecord).filter(
            LinkRecord.source_id == 'P1', LinkRecord.target_id == 'P2',
            LinkRecord.valid_to.is_(None)).count()
    assert ('P1', 'P2') not in replay_pairs
    assert live_rows == 0


def test_diff_detects_added_and_removed(db):
    """diff() compara dos INSTANTÁNEAS (qué está vigente en from vs en to), no
    'todo lo que pasó en el medio'. El vínculo Supplier→ACME vivió 2020-06→2022-06:
    - diff(2010,2021) debe mostrarlo como AÑADIDO (no vigente en 2010, sí en 2021).
    - diff(2021,2023) debe mostrarlo como QUITADO (vigente en 2021, no en 2023).
    - diff(2010,2023) NO debe mostrar cambio neto (inactivo en ambos extremos)."""
    from ontology.db import session_scope
    from ontology.service import diff_graph, _parse_dt

    with session_scope() as s:
        d_added = diff_graph(s, _parse_dt('2010-01-01'), _parse_dt('2021-01-01'))
        d_removed = diff_graph(s, _parse_dt('2021-01-01'), _parse_dt('2023-01-01'))
        d_net = diff_graph(s, _parse_dt('2010-01-01'), _parse_dt('2023-01-01'))

    assert ('Supplier', 'ACME') in {(a['source'], a['target']) for a in d_added['added']}
    assert ('Supplier', 'ACME') in {(r['source'], r['target']) for r in d_removed['removed']}
    assert ('Supplier', 'ACME') not in {(x['source'], x['target']) for x in d_net['added']}
    assert ('Supplier', 'ACME') not in {(x['source'], x['target']) for x in d_net['removed']}


def test_object_history_ordered(db):
    from ontology.db import session_scope
    from ontology.service import object_history

    with session_scope() as s:
        events = object_history(s, 'ACME')
    assert len(events) >= 2  # ObjectCreated + ObjectUpdated
    valid_froms = [e.valid_from for e in events]
    assert valid_froms == sorted(valid_froms)


def test_migration_is_isomorphic_with_grafo_v0():
    """Criterio de aceptación: la migración real (grafo_v0.json → Postgres)
    produce el mismo conteo de nodos/links que el snapshot exportado."""
    import json
    import subprocess

    graph_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'grafo_v0.json')
    if not os.path.exists(graph_path):
        pytest.skip('data/grafo_v0.json no existe — correr scripts/export_graph_v0.js primero')
    with open(graph_path) as f:
        g = json.load(f)

    from ontology.db import init_schema, session_scope, _get_engine
    from ontology.models import Base, ObjectRecord, LinkRecord
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()

    script = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'migrate_v0_to_ontology.py')
    result = subprocess.run([sys.executable, script, '--reset'], capture_output=True, text=True,
                             env={**os.environ, 'DATABASE_URL': DATABASE_URL})
    assert result.returncode == 0, result.stderr

    expected_objects = len(g['nodes']) + len((g.get('ontology') or {}).get('objects', []))
    with session_scope() as s:
        n_obj = s.query(ObjectRecord).count()
        n_link = s.query(LinkRecord).count()

    assert n_obj == expected_objects
    # links >= los base (algunos hechos temporales pueden duplicar pares, es esperado — ver docstring del script)
    assert n_link >= len(g['links'])
