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

# Tablas protegidas por kh_append_only (broker_audit tiene su propio disparador desde Phase 3). Paso 6: el
# libro de decisiones (ontology/ledger_models.py). decision_blobs tiene su propia guardia (purga por retención).
APPEND_ONLY_TABLES = ('events', 'kh_tx_versions', 'hot_view_builds',
                      'decisions', 'decision_refs', 'decision_outcomes', 'decision_violations',
                      'ledger_seals', 'ledger_meta', 'ledger_anchors',
                      'gov_artifacts', 'gov_releases')

# Tablas con txid/seq añadidos como columnas tardías (ontology/db._COLUMNAS_TARDIAS): aquí solo el DEFAULT.
TXID_SEQ_TABLES = ('events', 'broker_audit')

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


def _column_defaults(conn, table='events'):
    from sqlalchemy import text
    rows = conn.execute(text(
        "SELECT column_name, column_default FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = :t "
        "AND column_name IN ('txid', 'seq', 'release_hash')"), {'t': table}).all()
    return {c: d for c, d in rows}


def ensure_txid_seq(conn, table):
    """DEFAULT de <table>.txid/seq DESPUÉS de crear las columnas (las filas viejas quedan NULL = anteriores a
    la migración, nunca con un txid inventado). Idempotente. Devuelve {txid, seq} presentes."""
    cols = _column_defaults(conn, table)
    if 'txid' in cols and not cols['txid']:
        safe_ddl(conn, f'ALTER TABLE {table} ALTER COLUMN txid SET DEFAULT {txid_expr()}')
    if 'seq' in cols and not cols['seq']:
        if safe_ddl(conn, f'CREATE SEQUENCE IF NOT EXISTS {table}_seq_seq'):
            safe_ddl(conn, f"ALTER TABLE {table} ALTER COLUMN seq SET DEFAULT nextval('{table}_seq_seq')")
            safe_ddl(conn, f'ALTER SEQUENCE {table}_seq_seq OWNED BY {table}.seq')
    return cols


def ensure_events(conn):
    """DEFAULT de events.txid/seq (las columnas ya las creó _COLUMNAS_TARDIAS), índice parcial e índice por txid.
    Idempotente: solo toca lo que falta (un ALTER toma ACCESS EXCLUSIVE aunque no cambie nada)."""
    from sqlalchemy import text
    cols = ensure_txid_seq(conn, 'events')
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


# ── paso 6: libro de decisiones ─────────────────────────────────────────────
# decision_blobs: DELETE/TRUNCATE siempre prohibidos; UPDATE solo como PURGA por retención (§2.7): el job
# marca khipus.retention_job=on, el blob es standard_90d con > 90 días, queda body NULL con el MISMO sha y
# ninguna decisión 'sync' lo cita.
_FN_BLOB_GUARD = """
CREATE OR REPLACE FUNCTION kh_blob_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'UPDATE'
     AND coalesce(current_setting('khipus.retention_job', true), '') = 'on'
     AND OLD.retention_class = 'standard_90d'
     AND OLD.created_at < now() - interval '90 days'
     AND NEW.body IS NULL AND NEW.sha256 = OLD.sha256 AND NEW.kind = OLD.kind
     AND NEW.size_bytes = OLD.size_bytes AND NEW.retention_class = OLD.retention_class
     AND NEW.created_at = OLD.created_at
     AND NOT EXISTS (SELECT 1 FROM decision_refs r JOIN decisions d ON d.id = r.decision_id
                     WHERE r.ref_kind = 'blob' AND r.ref_id = OLD.sha256 AND d.durability = 'sync')
     AND NOT EXISTS (SELECT 1 FROM decisions d
                     WHERE d.durability = 'sync' AND (d.inputs_sha = OLD.sha256 OR d.output_sha = OLD.sha256))
  THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION 'decision_blobs es append-only: % no permitido (append-only; solo purga por retención)', TG_OP;
END $$
"""

_BLOB_TRIGGERS = """
DO $$
BEGIN
  IF to_regclass('decision_blobs') IS NOT NULL THEN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'decision_blobs_guard'
                   AND tgrelid = 'decision_blobs'::regclass) THEN
      CREATE TRIGGER decision_blobs_guard BEFORE UPDATE OR DELETE ON decision_blobs
        FOR EACH ROW EXECUTE PROCEDURE kh_blob_guard();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'decision_blobs_no_truncate'
                   AND tgrelid = 'decision_blobs'::regclass) THEN
      CREATE TRIGGER decision_blobs_no_truncate BEFORE TRUNCATE ON decision_blobs
        FOR EACH STATEMENT EXECUTE PROCEDURE kh_blob_guard();
    END IF;
  END IF;
END $$
"""

_LEDGER_INDEXES = (
    ('ix_dec_corr', 'CREATE INDEX IF NOT EXISTS ix_dec_corr ON decisions (correlation_id) '
                    'WHERE correlation_id IS NOT NULL'),
    ('ix_dec_parent', 'CREATE INDEX IF NOT EXISTS ix_dec_parent ON decisions (parent_id) WHERE parent_id IS NOT NULL'),
    ('ix_dec_pending', "CREATE INDEX IF NOT EXISTS ix_dec_pending ON decisions (recorded_at) "
                       "WHERE status = 'pending_approval'"),
    ('ix_dec_subject', 'CREATE INDEX IF NOT EXISTS ix_dec_subject ON decisions USING gin (subject jsonb_path_ops)'),
    ('ux_dout_dedup', "CREATE UNIQUE INDEX IF NOT EXISTS ux_dout_dedup ON decision_outcomes "
                      "(decision_id, outcome_kind, (result->>'dedup_key')) WHERE result ? 'dedup_key'"),
    ('ix_broker_audit_txid', 'CREATE INDEX IF NOT EXISTS ix_broker_audit_txid ON broker_audit (txid)'),
)


def ensure_ledger(conn):
    """Guardia de blobs, índices especiales del libro y DEFAULT de broker_audit.txid/seq. Idempotente."""
    from sqlalchemy import text
    if safe_ddl(conn, _FN_BLOB_GUARD):
        safe_ddl(conn, _BLOB_TRIGGERS)
    have = {n for (n,) in conn.execute(text(
        "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()")).all()}
    tables = {n for (n,) in conn.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()")).all()}
    for name, sql in _LEDGER_INDEXES:
        tbl = 'broker_audit' if name.startswith('ix_broker') else ('decision_outcomes' if 'dout' in name
                                                                   else 'decisions')
        if name not in have and tbl in tables:
            if tbl == 'broker_audit' and 'txid' not in _column_defaults(conn, 'broker_audit'):
                continue
            safe_ddl(conn, sql)
    if 'broker_audit' in tables:
        ensure_txid_seq(conn, 'broker_audit')


def blob_triggers_present(conn):
    from sqlalchemy import text
    rows = {n for (n,) in conn.execute(text(
        "SELECT t.tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
        "WHERE c.relname = 'decision_blobs' AND NOT t.tgisinternal")).all()}
    return {'decision_blobs_guard', 'decision_blobs_no_truncate'} <= rows


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
            ensure_ledger(conn)
            ok = ensure_append_only(conn) and ok
        STATE['ready'] = bool(ok)
        try:   # paso 6: el linaje del libro (ledger_meta) se crea una vez y se cachea en el proceso
            from core import ledger
            ledger.on_schema_init(engine)
        except Exception as e:  # noqa: BLE001
            log.warning('ledger_ddl: linaje no inicializado (%s)', type(e).__name__)
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
