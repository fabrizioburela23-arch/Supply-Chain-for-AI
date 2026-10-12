"""core/ledger_ddl.py — DDL idempotente de los registros que SOLO crecen (docs/INFRA_OPERATIVA.md §2.1, §4.3).

Generaliza el patrón probado de brokerage/models.py (broker_audit): cada paso de DDL va en su propio
SAVEPOINT y un fallo nunca tumba el arranque. Aquí viven:

  · la función genérica `kh_append_only()` y sus disparadores por tabla (`<t>_no_modify` BEFORE UPDATE OR
    DELETE por fila, `<t>_no_truncate` BEFORE TRUNCATE por sentencia) para `APPEND_ONLY_TABLES`;
  · las tablas del contador de versión del grafo (`kh_versions`, `kh_tx_versions`) y la bitácora de
    construcciones de vistas (`hot_view_builds`). Se crean con SQL propio (no con `Base.metadata`) para poder
    elegir el tipo de `txid` según la versión de Postgres: `xid8` + `pg_current_xact_id()` desde la 13
    (Railway usa 16); en una base más vieja, `bigint` + `txid_current()` y el 🩺 lo avisa;
  · `events.seq` (secuencia propia) y los DEFAULT de `events.txid`/`events.seq`. Las COLUMNAS se añaden en
    `ontology/db._COLUMNAS_TARDIAS` (regla del repo); aquí solo se pone el DEFAULT DESPUÉS de crear la
    columna: con `ADD COLUMN … DEFAULT pg_current_xact_id()` Postgres reescribiría la tabla y TODOS los
    eventos viejos quedarían con el txid de la migración (falso). Los eventos anteriores quedan con
    txid/seq NULL = "anteriores a la migración" (cuentan como versión 0 del grafo, §4.3);
  · el índice parcial de eventos estructurales `ix_events_structural` (§4.3, MAP 3 §3.4).

Nunca se borra ni se reescribe nada. Correcciones = eventos nuevos (`retracts_event_id`, LinkStatusChanged).
La única forma de "borrar" `events` sigue siendo el DROP de scripts/migrate_v0_to_ontology.reset_graph_tables
(exige el nombre exacto de la base; el disparador se va con la tabla y `init_schema` lo vuelve a crear).
"""
import logging

log = logging.getLogger('khipu')

# Tablas protegidas por kh_append_only (broker_audit tiene su propio disparador desde Phase 3).
APPEND_ONLY_TABLES = ('events', 'kh_tx_versions', 'hot_view_builds')

STRUCTURAL_EVENT_TYPES = ('ObjectCreated', 'ObjectUpdated', 'LinkCreated', 'LinkRemoved', 'LinkStatusChanged')

_FN_APPEND_ONLY = """
CREATE OR REPLACE FUNCTION kh_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION '% es append-only: % no permitido (append-only)', TG_TABLE_NAME, TG_OP;
END $$
"""

_TRIGGERS = """
DO $$
BEGIN
  IF to_regclass('{t}') IS NOT NULL THEN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = '{t}_no_modify' AND tgrelid = '{t}'::regclass) THEN
      CREATE TRIGGER {t}_no_modify BEFORE UPDATE OR DELETE ON {t}
        FOR EACH ROW EXECUTE PROCEDURE kh_append_only();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = '{t}_no_truncate' AND tgrelid = '{t}'::regclass) THEN
      CREATE TRIGGER {t}_no_truncate BEFORE TRUNCATE ON {t}
        FOR EACH STATEMENT EXECUTE PROCEDURE kh_append_only();
    END IF;
  END IF;
END $$
"""

# Estado del proceso: ¿la base soporta xid8? ¿están las tablas del contador? (lo lee core/hotviews/signals)
STATE = {'xid8': None, 'ready': False, 'server_version_num': None, 'last_error': None}


def txid_expr():
    """Expresión SQL del id de transacción actual según la base (xid8 desde Postgres 13)."""
    return 'pg_current_xact_id()' if STATE.get('xid8') is not False else 'txid_current()'


def _txid_type():
    return 'xid8' if STATE.get('xid8') is not False else 'bigint'


def safe_ddl(conn, sql, params=None):
    """Un paso de DDL en su SAVEPOINT: si falla, se registra y la transacción exterior sigue viva."""
    from sqlalchemy import text
    try:
        with conn.begin_nested():
            conn.execute(text(sql), params or {})
        return True
    except Exception as e:  # noqa: BLE001
        STATE['last_error'] = f'{type(e).__name__}: {str(e)[:200]}'
        log.warning('ledger_ddl: DDL no aplicado (%s): %s', type(e).__name__, str(e)[:160])
        return False


def detect_xid8(conn):
    """Postgres ≥ 13 tiene xid8/pg_current_xact_id(). Se mira server_version_num (§7: Railway usa 16)."""
    from sqlalchemy import text
    try:
        v = int(conn.execute(text('SHOW server_version_num')).scalar())
    except Exception:  # noqa: BLE001
        v = None
    STATE['server_version_num'] = v
    STATE['xid8'] = bool(v is None or v >= 130000)
    if v is not None and v < 130000:
        log.error('Postgres %s < 13: sin xid8 — txid como bigint; actualiza la base (Railway usa 16).', v)
    return STATE['xid8']


def _tables_sql():
    tt = _txid_type()
    return (
        # Contador de versión por nombre ('graph'). created_at es parte del linaje.
        """CREATE TABLE IF NOT EXISTS kh_versions (
             name varchar(16) PRIMARY KEY,
             v bigint NOT NULL DEFAULT 0,
             created_at timestamptz NOT NULL DEFAULT clock_timestamp())""",
        # Qué transacción confirmó cada versión (append-only): el orden de version ES el de confirmación.
        f"""CREATE TABLE IF NOT EXISTS kh_tx_versions (
             txid {tt} NOT NULL,
             name varchar(16) NOT NULL,
             version bigint NOT NULL,
             release_hash char(64),
             n_ids integer,
             committed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
             PRIMARY KEY (name, version),
             UNIQUE (txid, name))""",
        # Bitácora de construcciones de vistas (sin cuerpos): qué contenía cada vista.
        """CREATE TABLE IF NOT EXISTS hot_view_builds (
             id bigserial PRIMARY KEY,
             name varchar(32) NOT NULL,
             generation varchar(96) NOT NULL,
             graph_version bigint,
             release_hash char(64),
             source varchar(12) NOT NULL,
             content_sha char(64),
             n integer,
             build_ms integer,
             built_at timestamptz NOT NULL DEFAULT clock_timestamp())""",
        'CREATE INDEX IF NOT EXISTS ix_hot_view_builds_name ON hot_view_builds (name, built_at DESC)',
        "INSERT INTO kh_versions (name, v) VALUES ('graph', 0) ON CONFLICT (name) DO NOTHING",
    )


def _column_defaults(conn):
    from sqlalchemy import text
    rows = conn.execute(text(
        "SELECT column_name, column_default FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = 'events' "
        "AND column_name IN ('txid', 'seq', 'release_hash')")).all()
    return {c: d for c, d in rows}


def ensure_events(conn):
    """DEFAULT de events.txid/seq (las columnas ya las creó _COLUMNAS_TARDIAS), índice parcial e índice por txid.
    Idempotente: solo toca lo que falta (un ALTER toma ACCESS EXCLUSIVE aunque no cambie nada)."""
    from sqlalchemy import text
    cols = _column_defaults(conn)
    if 'txid' in cols and not cols['txid']:
        safe_ddl(conn, f'ALTER TABLE events ALTER COLUMN txid SET DEFAULT {txid_expr()}')
    if 'seq' in cols and not cols['seq']:
        if safe_ddl(conn, 'CREATE SEQUENCE IF NOT EXISTS events_seq_seq'):
            safe_ddl(conn, "ALTER TABLE events ALTER COLUMN seq SET DEFAULT nextval('events_seq_seq')")
            safe_ddl(conn, 'ALTER SEQUENCE events_seq_seq OWNED BY events.seq')
    idx = {n for (n,) in conn.execute(text(
        "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema() AND tablename = 'events'")).all()}
    types = ', '.join(f"'{t}'" for t in STRUCTURAL_EVENT_TYPES)
    if 'ix_events_structural' not in idx:
        safe_ddl(conn, f'CREATE INDEX IF NOT EXISTS ix_events_structural ON events (recorded_at DESC) '
                       f'WHERE event_type IN ({types})')
    if 'txid' in cols and 'ix_events_txid' not in idx:
        safe_ddl(conn, 'CREATE INDEX IF NOT EXISTS ix_events_txid ON events (txid)')
    if 'seq' in cols and 'ix_events_seq' not in idx:
        safe_ddl(conn, 'CREATE INDEX IF NOT EXISTS ix_events_seq ON events (seq)')


def ensure_append_only(conn, tables=APPEND_ONLY_TABLES):
    """kh_append_only() + disparadores en cada tabla existente de `tables` (idempotente)."""
    if not safe_ddl(conn, _FN_APPEND_ONLY):
        return False
    ok = True
    for t in tables:
        ok = safe_ddl(conn, _TRIGGERS.format(t=t)) and ok
    return ok


def ensure_all(engine):
    """Lo llama ontology.db.init_schema DESPUÉS de create_all y de las columnas tardías. Nunca lanza.
    Devuelve True si quedó todo (tablas del contador + disparadores)."""
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            conn.execute(text("SET LOCAL lock_timeout = '5s'"))
            detect_xid8(conn)
            ok = True
            for sql in _tables_sql():
                ok = safe_ddl(conn, sql) and ok
            ensure_events(conn)
            ok = ensure_append_only(conn) and ok
        STATE['ready'] = bool(ok)
        return STATE['ready']
    except Exception as e:  # noqa: BLE001
        STATE['ready'] = False
        STATE['last_error'] = f'{type(e).__name__}: {str(e)[:200]}'
        log.warning('ledger_ddl.ensure_all falló (la app sigue): %s', STATE['last_error'])
        return False


def triggers_present(conn, tables=APPEND_ONLY_TABLES):
    """{tabla: bool} — para el 🩺 y las pruebas."""
    from sqlalchemy import text
    rows = conn.execute(text(
        "SELECT c.relname, t.tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
        "WHERE NOT t.tgisinternal")).all()
    have = {(r, n) for r, n in rows}
    return {t: (t, f'{t}_no_modify') in have and (t, f'{t}_no_truncate') in have for t in tables}
