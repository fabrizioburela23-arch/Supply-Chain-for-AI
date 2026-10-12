"""tests/test_ops_graph_version.py — INFRA_OPERATIVA paso 2: graph_version se toma AL CONFIRMAR.

Garantiza (docs/INFRA_OPERATIVA.md §4.3, §9):
  · un evento económico mueve la versión UNA vez por transacción (no por evento), y deja su fila en
    kh_tx_versions con el MISMO txid que sus eventos (la junta que usará G(t, κ));
  · noticia, simulación guardada, nota y ActionExecuted solos NO la mueven; ConfirmarVinculo SÍ;
  · carrera de commits: si A escribe primero y B confirma antes, B recibe la versión menor (el orden de
    version ES el de confirmación — con MAX(recorded_at) la escritura de A quedaba invisible);
  · rollback → ni versión ni señal; after_commit avisa a los suscriptores; NOTIFY llega a un LISTEN;
  · graph_key cambia con lo económico, no con lo demás, y cambia de linaje si la tabla events se re-crea;
  · `_graph_epoch` ya no existe (prueba estática).
"""
import os
import select
import sys
import time

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
        for oid in ('GV_A', 'GV_B', 'GV_C'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=oid)
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 2.0,
                                       'properties': {'rel_label': 'Posible proveedor'}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='GV_A', target_id='GV_B')
    yield engine
    Base.metadata.drop_all(engine)


def _v(engine):
    from sqlalchemy import text
    with engine.begin() as c:
        return c.execute(text("SELECT v FROM kh_versions WHERE name = 'graph'")).scalar()


@needs_db
def test_un_commit_economico_es_una_version_con_su_txid(db):
    from sqlalchemy import text

    from ontology.db import session_scope
    from ontology.service import apply_event
    v0 = _v(db)
    with session_scope() as s:
        for i in range(3):          # tres eventos económicos, UNA transacción
            apply_event(s, 'ObjectUpdated', {'properties': {'margin': 0.1 * i}}, valid_from='2026-01-01',
                        source='test', actor='pytest', object_id='GV_C')
    assert _v(db) == v0 + 1
    with db.begin() as c:
        tv = c.execute(text("SELECT txid::text, version, release_hash, n_ids FROM kh_tx_versions "
                            "WHERE name = 'graph' AND version = :v"), {'v': v0 + 1}).first()
        ev_tx = {r[0] for r in c.execute(text(
            "SELECT txid::text FROM events WHERE object_id = 'GV_C' AND event_type = 'ObjectUpdated'")).all()}
    assert tv is not None and ev_tx == {tv[0]}            # la versión se junta con sus eventos por txid
    assert tv[2] and len(tv[2]) == 64 and tv[3] == 1


@needs_db
@pytest.mark.parametrize('what', ['news', 'simulation', 'annotation', 'action_only'])
def test_lo_no_economico_no_mueve_la_version(db, what):
    from ontology.actions import execute_action
    from ontology.db import session_scope
    from ontology.service import apply_event
    v0 = _v(db)
    with session_scope() as s:
        if what == 'news':           # noticia + su vínculo 'about' (W10, la escritura más frecuente)
            nid = f'news_{time.time_ns()}'
            apply_event(s, 'ObjectCreated', {'label': 'Titular', 'type': 'NewsItem'}, valid_from='2026-01-01',
                        source='gdelt', actor='pytest', object_id=nid)
            apply_event(s, 'LinkCreated', {'rel_type': 'about'}, valid_from='2026-01-01', source='gdelt',
                        actor='pytest', object_id=nid, target_id='GV_A')
        elif what == 'simulation':
            apply_event(s, 'ObjectCreated', {'label': 'Sim', 'type': 'Simulation', 'properties': {}},
                        valid_from='2026-01-01', source='livesim', actor='pytest', object_id=f'sim_{time.time_ns()}')
        elif what == 'annotation':
            execute_action(s, 'AnotarObjeto', {'object_id': 'GV_A', 'texto': 'nota'}, actor='pytest')
        else:
            apply_event(s, 'ActionExecuted', {'action': 'Nada'}, valid_from='2026-01-01', source='test',
                        actor='pytest', object_id='GV_A')
    assert _v(db) == v0, what


@needs_db
def test_confirmar_vinculo_si_mueve_la_version(db):
    from ontology.actions import execute_action
    from ontology.db import session_scope
    from ontology.models import LinkRecord
    with session_scope() as s:
        lid = str(s.query(LinkRecord).filter_by(source_id='GV_A', target_id='GV_B').first().id)
    v0 = _v(db)
    with session_scope() as s:
        execute_action(s, 'ConfirmarVinculo', {'link_id': lid}, actor='fabrizio')
    assert _v(db) == v0 + 1


@needs_db
def test_carrera_el_orden_de_version_es_el_orden_de_confirmacion(db):
    from sqlalchemy import text

    from ontology.db import get_session_factory
    from ontology.service import apply_event
    f = get_session_factory()
    a, b = f(), f()
    try:
        apply_event(a, 'ObjectUpdated', {'properties': {'r': 'A'}}, valid_from='2026-02-01', source='test',
                    actor='A', object_id='GV_A')
        a.flush()                                   # A escribió PRIMERO (recorded_at menor)…
        apply_event(b, 'ObjectUpdated', {'properties': {'r': 'B'}}, valid_from='2026-02-01', source='test',
                    actor='B', object_id='GV_B')
        b.commit()                                  # …pero B confirma antes (A no tomó ningún candado)
        a.commit()
    finally:
        a.close()
        b.close()
    with db.begin() as c:
        rows = dict(c.execute(text(
            "SELECT e.actor, tv.version FROM events e JOIN kh_tx_versions tv ON tv.txid = e.txid "
            "AND tv.name = 'graph' WHERE e.actor IN ('A', 'B') AND e.valid_from = '2026-02-01'")).all())
        rec = dict(c.execute(text("SELECT actor, recorded_at FROM events WHERE actor IN ('A', 'B') "
                                  "AND valid_from = '2026-02-01'")).all())
    assert rec['A'] < rec['B']                     # MAX(recorded_at) habría quedado en B y "perdido" a A
    assert rows['B'] < rows['A']                    # la versión sigue la confirmación


@needs_db
def test_rollback_no_mueve_ni_avisa_y_commit_avisa(db):
    from core.hotviews import signals
    from ontology.db import session_scope
    from ontology.service import apply_event
    got = []
    fn = lambda name, v, ids: got.append((name, v, tuple(ids)))  # noqa: E731
    signals.subscribe(fn)
    try:
        v0 = _v(db)
        with pytest.raises(RuntimeError):
            with session_scope() as s:
                apply_event(s, 'ObjectUpdated', {'properties': {'x': 1}}, valid_from='2026-03-01', source='test',
                            actor='pytest', object_id='GV_A')
                raise RuntimeError('aborta')
        assert _v(db) == v0 and got == []
        with session_scope() as s:
            apply_event(s, 'ObjectUpdated', {'properties': {'x': 2}}, valid_from='2026-03-01', source='test',
                        actor='pytest', object_id='GV_A')
        assert got and got[-1][0] == 'graph' and got[-1][1] == v0 + 1 and 'GV_A' in got[-1][2]
        assert signals.known()['v'] >= v0 + 1
    finally:
        signals._SUBSCRIBERS.remove(fn)


@needs_db
def test_notify_llega_a_un_listen_al_confirmar(db):
    import json

    import psycopg2

    from core.hotviews import signals
    from ontology.db import session_scope
    from ontology.service import apply_event
    conn = psycopg2.connect(signals._dsn())
    conn.set_isolation_level(0)
    try:
        with conn.cursor() as cur:
            cur.execute(f'LISTEN {signals.CHANNEL}')
        v0 = _v(db)
        with session_scope() as s:
            apply_event(s, 'LinkCreated', {'rel_type': 'fab', 'weight': 3.0}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id='GV_B', target_id='GV_C')
        deadline, got = time.time() + 5, None
        while time.time() < deadline and got is None:
            if select.select([conn], [], [], 0.5)[0]:
                conn.poll()
                while conn.notifies:
                    n = conn.notifies.pop(0)
                    if n.channel == signals.CHANNEL:
                        got = json.loads(n.payload)
        assert got is not None and got['v'] == v0 + 1 and {'GV_B', 'GV_C'} <= set(got['ids'])
    finally:
        conn.close()


@needs_db
def test_graph_key_sigue_lo_economico_y_el_linaje(db):
    from matrix.engine import graph_key
    from ontology.db import session_scope
    from ontology.service import apply_event
    with session_scope() as s:
        k0 = graph_key(s)
    assert k0.startswith('g') and '.l' in k0 and '.r' in k0
    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': 'n', 'type': 'NewsItem'}, valid_from='2026-01-01', source='t',
                    actor='t', object_id=f'news_k{time.time_ns()}')
    with session_scope() as s:
        assert graph_key(s) == k0                    # una noticia no invalida matrices/insights/métricas
    with session_scope() as s:
        apply_event(s, 'ObjectUpdated', {'properties': {'country': 'TW'}}, valid_from='2026-01-01', source='t',
                    actor='t', object_id='GV_C')
    with session_scope() as s:
        k1 = graph_key(s)
    assert k1 != k0
    # una tabla events re-creada es OTRO linaje aunque el contador no retroceda
    from sqlalchemy import text
    with db.begin() as c:
        oid_before = c.execute(text("SELECT to_regclass('events')::oid")).scalar()
    lineage_before = k1.split('.l', 1)[1].split('.r', 1)[0]
    assert lineage_before.startswith(f'{oid_before}.')


def test_graph_epoch_ya_no_existe():
    import matrix.engine as E
    assert not hasattr(E, '_graph_epoch') and hasattr(E, 'graph_key')
    for rel in ('matrix/engine.py', 'matrix/api.py'):
        src = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        code = '\n'.join(l for l in src.splitlines() if not l.lstrip().startswith('#'))
        assert '_graph_epoch(' not in code, rel
