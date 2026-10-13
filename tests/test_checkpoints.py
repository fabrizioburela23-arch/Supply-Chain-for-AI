"""tests/test_checkpoints.py — INFRA_OPERATIVA paso 26: puntos de control del grafo (ontology/checkpoints.py).

  · APAGADOS por debajo del umbral (ledger.retention.checkpoint_min_events = 20.000; producción ~5.000): ni una
    consulta extra en /api/ontology/graph y la tarea del reloj no construye nada;
  · con el umbral bajado (prueba del mecanismo): la foto se guarda comprimida con su sha256 (append-only) y una
    consulta as_of se sirve desde ella SOLO si da exactamente lo mismo que el pliegue de siempre (paridad);
  · un evento nuevo, o un evento con fecha dentro de la ventana consultada, la invalida (vuelve al pliegue).
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


def test_umbral_por_defecto_y_apagado():
    from core import governance
    from ontology import checkpoints
    governance._reset_for_tests()
    checkpoints._reset_for_tests()
    p = checkpoints.params()
    assert p['checkpoint_min_events'] == 20000 and p['checkpoint_every_events'] == 10000
    assert checkpoints.lookup(None, datetime.now(timezone.utc)) is None     # apagado: ni toca la sesión


@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from core import governance
    from ontology import checkpoints
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    governance._reset_for_tests()
    checkpoints._reset_for_tests()
    assert init_schema(retries=1)
    with session_scope() as s:
        for oid in ('CP_A', 'CP_B', 'CP_C'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=oid)
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 3}, valid_from='2020-01-01', source='test',
                    actor='pytest', object_id='CP_A', target_id='CP_B')
        apply_event(s, 'LinkCreated', {'rel_type': 'fab', 'weight': 4}, valid_from='2022-06-01', source='test',
                    actor='pytest', object_id='CP_B', target_id='CP_C')
    yield engine
    checkpoints._reset_for_tests()
    governance._reset_for_tests()
    Base.metadata.drop_all(engine)


def _strip(g):
    return {k: v for k, v in g.items() if k not in ('as_of', 'checkpoint')}


def _norm(g):
    g = _strip(g)
    return {**g, 'nodes': sorted(g['nodes'], key=lambda n: n['id']),
            'links': sorted(g['links'], key=lambda l: (l['source'], l['target'], l['rel_type']))}


@needs_db
def test_por_debajo_del_umbral_no_construye(db):
    from ontology import checkpoints
    out = checkpoints.job()
    assert out['skipped'] == 'below_threshold' and out['threshold'] == 20000
    assert checkpoints.STATE['enabled'] is False


@needs_db
def test_paridad_exacta_e_invalidacion(db):
    from sqlalchemy import text

    from ontology import checkpoints
    from ontology.db import session_scope
    from ontology.service import apply_event, as_of_graph
    with session_scope() as s:
        assert checkpoints.refresh_state(s, min_events=1)               # umbral bajado SOLO en la prueba
        meta = checkpoints.build(s)
    assert meta['n_links'] == 2 and meta['n_nodes'] == 3 and len(meta['sha256']) == 64
    now = datetime.now(timezone.utc)
    with session_scope() as s:
        hit = checkpoints.lookup(s, now)
        assert hit is not None and hit['checkpoint']['id'] == meta['id']
        assert _norm(hit) == _norm(as_of_graph(s, now))                  # paridad con el pliegue
        # ventana sin eventos (2023 → hoy): misma foto
        t = datetime(2023, 1, 1, tzinfo=timezone.utc)
        h2 = checkpoints.lookup(s, t)
        assert h2 is not None and _norm(h2) == _norm(as_of_graph(s, t))
        # ventana con un evento (2021 → hoy contiene el vínculo de 2022): pliegue
        assert checkpoints.lookup(s, datetime(2021, 1, 1, tzinfo=timezone.utc)) is None
    with session_scope() as s:                                           # un evento nuevo invalida la foto
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 2}, valid_from='2019-01-01', source='test',
                    actor='pytest', object_id='CP_C', target_id='CP_A')
    with session_scope() as s:
        assert checkpoints.lookup(s, now + timedelta(seconds=1)) is None
        meta2 = checkpoints.build(s)
        assert meta2['n_links'] == 3
        assert _norm(checkpoints.lookup(s, now)) == _norm(as_of_graph(s, now))
    with db.connect() as c:
        assert c.execute(text('SELECT count(*) FROM graph_checkpoints')).scalar() == 2
    for sql in ('UPDATE graph_checkpoints SET n_links = 0', 'DELETE FROM graph_checkpoints'):
        with pytest.raises(Exception):
            with db.begin() as c:
                c.execute(text(sql))


@needs_db
def test_api_graph_usa_el_punto_de_control_solo_si_esta_encendido(db):
    import server
    from ontology import checkpoints
    c = server.app.test_client()
    checkpoints.STATE['enabled'] = True
    try:
        r = c.get('/api/ontology/graph')
        assert r.status_code == 200 and 'checkpoint' in r.get_json()
    finally:
        checkpoints.STATE['enabled'] = False
    r2 = c.get('/api/ontology/graph')
    assert r2.status_code == 200 and 'checkpoint' not in r2.get_json()
    assert _norm(r.get_json()) == _norm(r2.get_json())
