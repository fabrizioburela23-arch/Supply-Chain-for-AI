"""tests/test_ops_events_append_only.py — INFRA_OPERATIVA paso 1: el registro de eventos es inmutable EN LA BASE.

Garantiza (docs/INFRA_OPERATIVA.md §9):
  · UPDATE, DELETE y TRUNCATE fallan en `events` y en cada tabla de core/ledger_ddl.APPEND_ONLY_TABLES
    (también desde SQL crudo, no solo desde el ORM);
  · `events.txid`/`seq` se llenan solos para los eventos nuevos y los VIEJOS quedan NULL (la migración de
    una base existente no reescribe la tabla ni les inventa un txid);
  · la migración es idempotente (dos arranques seguidos) y deja el índice parcial de eventos estructurales;
  · ningún camino del código de producción hace UPDATE/DELETE sobre `events` (prueba estática).

Requiere Postgres (DATABASE_URL); se salta sin base, como el resto de pruebas de ontología.
"""
import os
import re
import sys

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
        for oid in ('AO_A', 'AO_B'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=oid)
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 2.0}, valid_from='2000-01-01',
                    source='test', actor='pytest', object_id='AO_A', target_id='AO_B')
    yield engine
    Base.metadata.drop_all(engine)


def _fails(engine, sql):
    """Ejecuta `sql` en su propia transacción; devuelve el mensaje de error (o None si NO falló)."""
    from sqlalchemy import text
    try:
        with engine.begin() as c:
            c.execute(text(sql))
    except Exception as e:  # noqa: BLE001
        return str(e)
    return None


@needs_db
@pytest.mark.parametrize('sql', [
    "UPDATE events SET actor = 'hacker'",
    "UPDATE events SET payload = '{}'::jsonb WHERE event_type = 'LinkCreated'",
    'DELETE FROM events',
    "DELETE FROM events WHERE event_type = 'ObjectCreated'",
    'TRUNCATE events',
])
def test_events_rechaza_update_delete_truncate(db, sql):
    err = _fails(db, sql)
    assert err is not None and 'append-only' in err, (sql, err)


@needs_db
def test_cada_tabla_append_only_tiene_sus_dos_disparadores_y_los_hace_cumplir(db):
    from sqlalchemy import text

    from core import ledger_ddl
    with db.begin() as c:
        have = ledger_ddl.triggers_present(c)
        c.execute(text("INSERT INTO hot_view_builds (name, generation, source) VALUES ('t', 'g0.rx.test', 'test')"))
    assert set(have) == set(ledger_ddl.APPEND_ONLY_TABLES) and all(have.values()), have
    # kh_tx_versions ya tiene filas: el fixture confirmó eventos económicos
    with db.begin() as c:
        assert c.execute(text('SELECT count(*) FROM kh_tx_versions')).scalar() >= 1
    for t in ('kh_tx_versions', 'hot_view_builds'):
        for sql in (f'UPDATE {t} SET name = name', f'DELETE FROM {t}', f'TRUNCATE {t}'):
            err = _fails(db, sql)
            assert err is not None and 'append-only' in err, (sql, err)


@needs_db
def test_insertar_sigue_funcionando_y_txid_seq_se_llenan_solos(db):
    from sqlalchemy import text

    from ontology.db import session_scope
    from ontology.service import apply_event
    with session_scope() as s:
        apply_event(s, 'ObjectUpdated', {'properties': {'margin': 0.3}}, valid_from='2026-01-01',
                    source='test', actor='pytest', object_id='AO_A')
        apply_event(s, 'ObjectUpdated', {'properties': {'margin': 0.31}}, valid_from='2026-01-02',
                    source='test', actor='pytest', object_id='AO_A')
    with db.begin() as c:
        rows = c.execute(text("SELECT txid::text, seq FROM events WHERE object_id = 'AO_A' "
                              "AND event_type = 'ObjectUpdated' ORDER BY seq")).all()
    assert len(rows) == 2
    assert all(r[0] for r in rows) and rows[0][0] == rows[1][0]        # misma transacción → mismo txid
    assert rows[0][1] < rows[1][1]                                       # orden total de inserción


@needs_db
def test_migracion_de_una_base_existente_es_segura_e_idempotente(db):
    """Simula la base de PRODUCCIÓN anterior al paso 1 (sin columnas, sin disparadores, sin índice) con un
    evento viejo; init_schema lo migra sin reescribir ese evento (txid/seq NULL = 'antes de la migración')."""
    from sqlalchemy import text

    from ontology.db import init_schema, schema_outdated
    with db.begin() as c:
        c.execute(text('DROP TRIGGER IF EXISTS events_no_modify ON events'))
        c.execute(text('DROP TRIGGER IF EXISTS events_no_truncate ON events'))
        c.execute(text('DROP INDEX IF EXISTS ix_events_structural'))
        for col in ('txid', 'seq', 'release_hash'):
            c.execute(text(f'ALTER TABLE events DROP COLUMN IF EXISTS {col}'))
        c.execute(text('DROP SEQUENCE IF EXISTS events_seq_seq'))
        c.execute(text(
            "INSERT INTO events (id, event_type, object_id, payload, valid_from, recorded_at, source, actor) "
            "VALUES (gen_random_uuid(), 'ObjectUpdated', 'AO_B', '{\"properties\": {\"old\": true}}'::jsonb, "
            "'2020-01-01', now(), 'legacy', 'legacy')"))
    assert {'events.txid', 'events.seq', 'events.release_hash'} <= set(schema_outdated())
    assert _fails(db, "UPDATE events SET actor = 'x' WHERE source = 'legacy'") is None   # sin disparador aún
    assert init_schema(retries=1)
    assert init_schema(retries=1)                     # idempotente: el segundo arranque no cambia nada
    assert schema_outdated() == []
    with db.begin() as c:
        old = c.execute(text("SELECT txid, seq FROM events WHERE source = 'legacy'")).first()
        idx = c.execute(text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_events_structural'")).scalar()
        dflt = dict(c.execute(text(
            "SELECT column_name, column_default FROM information_schema.columns WHERE table_name = 'events' "
            "AND column_name IN ('txid', 'seq')")).all())
    assert old == (None, None)                        # el evento viejo NO recibió el txid de la migración
    assert idx and 'WHERE' in idx and 'LinkStatusChanged' in idx and 'recorded_at DESC' in idx
    assert 'pg_current_xact_id' in (dflt['txid'] or '') and 'nextval' in (dflt['seq'] or '')
    err = _fails(db, "UPDATE events SET actor = 'x' WHERE source = 'legacy'")
    assert err is not None and 'append-only' in err


def test_ningun_camino_de_produccion_hace_update_o_delete_de_events():
    """Prueba estática: nadie escribe UPDATE/DELETE/TRUNCATE sobre `events`, ni por SQL ni por el ORM
    (correcciones = eventos nuevos). La única puerta destructiva es el DROP protegido de la re-migración."""
    pat_sql = re.compile(r'(UPDATE\s+events\b|DELETE\s+FROM\s+events\b|TRUNCATE\s+(TABLE\s+)?events\b)', re.I)
    pat_orm = re.compile(r'(query\(Event\)[^\n]*\.(delete|update)\(|(delete|update)\(Event\b|'
                         r'Event\.__table__\.(delete|update)\()')
    offenders = []
    for base in ('ontology', 'core', 'matrix', 'research', 'mcp_server', 'brokerage', 'scripts'):
        for dirpath, _, files in os.walk(os.path.join(ROOT, base)):
            for fn in files:
                if not fn.endswith('.py'):
                    continue
                path = os.path.join(dirpath, fn)
                src = open(path, encoding='utf-8').read()
                for m in list(pat_sql.finditer(src)) + list(pat_orm.finditer(src)):
                    offenders.append(f'{os.path.relpath(path, ROOT)}: {m.group(0)}')
    src = open(os.path.join(ROOT, 'server.py'), encoding='utf-8').read()
    offenders += [f'server.py: {m.group(0)}' for m in pat_sql.finditer(src)]
    assert offenders == [], offenders


def test_el_disparador_no_se_puede_saltar_con_una_columna_tardia_con_default():
    """La columna txid se añade SIN default y el default va después (no reescribe ni inventa txids)."""
    from ontology.db import _COLUMNAS_TARDIAS
    cols = {(t, c): typ for t, c, typ in _COLUMNAS_TARDIAS}
    assert cols[('events', 'txid')] == 'XID8' and 'DEFAULT' not in cols[('events', 'txid')].upper()
    assert cols[('events', 'seq')] == 'BIGINT'
    assert cols[('events', 'release_hash')] == 'CHAR(64)'
