"""ontology/db.py — conexión a Postgres (fuente única de verdad de la ontología).

Sigue el mismo patrón de "feature opcional" que Neo4j (server.py:_temporal_mode):
si DATABASE_URL no está configurada, la ontología queda inactiva sin romper
el resto de la app. Railway inyecta DATABASE_URL automáticamente al añadir
el plugin de Postgres al proyecto.
"""
import logging
import os
from contextlib import contextmanager

log = logging.getLogger('khipu')

DATABASE_URL = os.getenv('DATABASE_URL', '')

_engine = None
_SessionLocal = None


def ontology_available():
    return bool(DATABASE_URL)


def _normalize_url(url):
    """Esquema → driver INSTALADO. Railway a veces entrega postgres:// (viejo) y
    algunas plantillas usan postgresql+psycopg:// (psycopg 3), que NO está en
    requirements (usamos psycopg2-binary) → 'No module named psycopg' en prod
    (2026-09-28). Si el driver pedido no existe, se usa psycopg2."""
    if '://' not in url:
        return url
    scheme, rest = url.split('://', 1)
    base, _, driver = scheme.partition('+')
    if base in ('postgres', 'postgresql'):
        base = 'postgresql'
        if driver:
            try:
                __import__({'psycopg': 'psycopg', 'psycopg2': 'psycopg2', 'asyncpg': 'asyncpg',
                            'pg8000': 'pg8000'}.get(driver, driver))
                if driver == 'asyncpg':
                    raise ImportError('asyncpg no sirve con un engine síncrono')
            except ImportError:
                driver = ''
        if not driver:
            # SQLAlchemy 2.1 cambió el driver POR DEFECTO de postgresql:// a
            # psycopg 3 → hay que nombrar psycopg2 explícitamente.
            try:
                __import__('psycopg2')
                driver = 'psycopg2'
            except ImportError:
                pass
        return f'{base}+{driver}://{rest}' if driver else f'{base}://{rest}'
    return url


def _env_int(name, default, lo, hi):
    try:
        v = int(os.getenv(name, default))
    except (TypeError, ValueError):
        v = default
    return max(lo, min(hi, v))


# Límites anti-hambre-de-hilos (auditoría estructural 2026-09-30, #2): gunicorn
# corre 1 worker con pocos hilos; sin estos topes una base lenta o caída dejaba
# cada hilo esperando indefinidamente (conexión, cupo del pool o consulta).
DB_POOL_TIMEOUT_S = _env_int('DB_POOL_TIMEOUT_S', 10, 1, 120)          # esperar cupo del pool
DB_CONNECT_TIMEOUT_S = _env_int('DB_CONNECT_TIMEOUT_S', 5, 1, 60)      # abrir la conexión TCP
DB_STATEMENT_TIMEOUT_MS = _env_int('DB_STATEMENT_TIMEOUT_MS', 30000, 1000, 600000)  # cada consulta
# Tamaño del pool (revisión 2026-09-30): gunicorn pasó a 12 hilos y además hay
# hilos de fondo con sesión abierta (research, comité, ciclo de agentes,
# warmers). Con 5+5 = 10 conexiones y pool_timeout 10 s, 10+ usuarios de la base
# a la vez daban QueuePool TimeoutError (500). 10+10 = 20 cubre los 12 hilos +
# el fondo; el Postgres de Railway admite 100 conexiones. Ajustables sin tocar
# código con DB_POOL_SIZE / DB_MAX_OVERFLOW.
DB_POOL_SIZE = _env_int('DB_POOL_SIZE', 10, 1, 50)
DB_MAX_OVERFLOW = _env_int('DB_MAX_OVERFLOW', 10, 0, 50)


def _engine_kwargs(url):
    """Opciones del engine. connect_timeout/statement_timeout son parámetros de
    libpq: solo se pasan con psycopg2/psycopg (con otro driver romperían)."""
    kw = dict(pool_pre_ping=True, pool_size=DB_POOL_SIZE, max_overflow=DB_MAX_OVERFLOW,
              pool_timeout=DB_POOL_TIMEOUT_S, pool_recycle=1800)
    if url.startswith('postgresql+psycopg2://') or url.startswith('postgresql+psycopg://'):
        kw['connect_args'] = {'connect_timeout': DB_CONNECT_TIMEOUT_S,
                              'options': f'-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}'}
    return kw


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        url = DATABASE_URL
        # Railway a veces entrega postgres:// (esquema viejo); SQLAlchemy 1.4+/2.x
        # requiere postgresql://
        url = _normalize_url(url)
        _engine = create_engine(url, **_engine_kwargs(url))
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_session_factory():
    _get_engine()
    return _SessionLocal


@contextmanager
def session_scope():
    """Sesión con commit/rollback automático. Uso: with session_scope() as s: ..."""
    factory = get_session_factory()
    s = factory()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


# Columnas añadidas DESPUÉS de que una tabla ya existía en producción.
# `create_all` solo crea tablas nuevas: NO añade columnas a las que ya están,
# así que una base viva se quedaría sin ellas y el ORM reventaría al leer.
# Se aplican con ADD COLUMN IF NOT EXISTS (idempotente, no destructivo).
_COLUMNAS_TARDIAS = (
    # Phase 1 · M1 — procedencia (ver ontology/provenance.py)
    ('events', 'source_id', 'VARCHAR(120)'),
    ('events', 'confidence', 'DOUBLE PRECISION'),
    # C8 (misión de reparación 2026-10-04) — falsadores verificables
    ('research_claims', 'falsifier_rules', 'JSONB'),
    # G2 — retracción dirigida de UNA fila de links
    ('links', 'event_id', 'UUID'),
    # limpieza 2026-10-11 — preguntas abiertas del analista fuera de `errors`
    ('agent_runs', 'open_questions', 'JSONB'),
    # INFRA_OPERATIVA paso 1 (2026-10-12) — registro de eventos inmutable. Se añaden SIN default (no se
    # reescribe la tabla ni se inventa un txid para los eventos viejos: quedan NULL = "antes de la
    # migración", versión 0 del grafo); core/ledger_ddl.ensure_events pone el DEFAULT después.
    ('events', 'txid', 'XID8'),            # → BIGINT en Postgres < 13 (ver init_schema)
    ('events', 'seq', 'BIGINT'),
    ('events', 'release_hash', 'CHAR(64)'),
    # INFRA_OPERATIVA paso 6 — broker_audit entra a la cadena de sellos: txid/seq (DEFAULT en core/ledger_ddl)
    ('broker_audit', 'txid', 'XID8'),
    ('broker_audit', 'seq', 'BIGINT'),
    # INFRA_OPERATIVA paso 10 — G-PROP: el GateReport de la propuesta queda adjunto para quien la apruebe
    ('proposed_actions', 'gate_report', 'JSONB'),
    # INFRA_OPERATIVA pasos 15-17 — un solo camino de órdenes: canal, modo de controles, release al previsualizar,
    # decisiones del libro y prueba de lectura por voz de cada orden (brokerage/models.BrokerOrder.meta)
    ('broker_orders', 'meta', 'JSONB'),
)


def schema_outdated(engine=None):
    """¿Falta alguna de las columnas tardías? Permite detectar una base con el
    esquema viejo SIN tener que provocar el error en una consulta real."""
    import warnings

    from sqlalchemy import exc as sa_exc, inspect
    try:
        insp = inspect(engine or _get_engine())
        existentes = set(insp.get_table_names())
        faltan = []
        for tabla, columna, _tipo in _COLUMNAS_TARDIAS:
            if tabla not in existentes:
                continue          # la tabla aún no existe: create_all la hará completa
            with warnings.catch_warnings():      # events.txid es xid8: el inspector no conoce el tipo (inocuo)
                warnings.simplefilter('ignore', sa_exc.SAWarning)
                cols = {c['name'] for c in insp.get_columns(tabla)}
            if columna not in cols:
                faltan.append(f'{tabla}.{columna}')
        return faltan
    except Exception:  # noqa: BLE001
        return []     # si no se puede inspeccionar, no afirmamos nada


def init_schema(retries=6, delay=2.0):
    """Crea/actualiza el esquema (idempotente). Se llama al arrancar el server
    y desde el script de migración.

    REINTENTA a propósito: Railway arranca la app y Postgres EN PARALELO, así
    que el primer intento puede encontrar la base todavía sin aceptar
    conexiones. Sin reintento el esquema se quedaba sin actualizar hasta el
    siguiente despliegue, y los endpoints fallaban con
    'column events.source_id does not exist' — pasó en producción (sept-2026).

    Nunca impide el arranque: si tras los reintentos sigue fallando, se registra
    y la app sigue (el resto de la app no depende de la ontología)."""
    import time as _time

    from sqlalchemy import text
    from ontology.models import Base
    try:
        import research.models  # noqa: F401 — Phase 2: registra research_* en el mismo Base
    except Exception as e:  # noqa: BLE001
        log.warning('init_schema: research.models no cargó (%s)', type(e).__name__)
    for _m in ('brokerage.models', 'mcp_server.models', 'core.ops_check'):   # Phase 3 + O1 (ops_checks), opcionales
        try:
            __import__(_m)
        except Exception as e:  # noqa: BLE001
            log.warning('init_schema: %s no cargó (%s)', _m, type(e).__name__)

    ultimo = None
    for intento in range(1, max(1, retries) + 1):
        try:
            engine = _get_engine()
            try:   # paso 6: xid8 o bigint para las columnas txid del libro (lo decide la versión de Postgres)
                from core import ledger_ddl as _ldd
                with engine.connect() as _c:
                    _ldd.detect_xid8(_c)
            except Exception:  # noqa: BLE001
                pass
            Base.metadata.create_all(engine)

            with engine.begin() as conn:
                # G5 (revisión de despliegue): ALTER TABLE … IF NOT EXISTS toma un candado
                # ACCESS EXCLUSIVE AUNQUE la columna exista — en cada arranque, con el
                # contenedor viejo atendiendo. Solo se altera lo que falta, y con un
                # lock_timeout corto: si una transacción larga tiene la tabla, se reintenta.
                conn.execute(text("SET LOCAL lock_timeout = '5s'"))
                existentes = {(t, c) for t, c in conn.execute(text(
                    "SELECT table_name, column_name FROM information_schema.columns "
                    "WHERE table_schema = current_schema()")).all()}
                try:     # xid8 existe desde Postgres 13 (Railway usa 16); en una base vieja, bigint
                    _pgv = int(conn.execute(text('SHOW server_version_num')).scalar())
                except Exception:  # noqa: BLE001
                    _pgv = None
                tablas = {t for t, _c in existentes}
                for tabla, columna, tipo in _COLUMNAS_TARDIAS:
                    if tabla in tablas and (tabla, columna) not in existentes:
                        if tipo == 'XID8' and _pgv is not None and _pgv < 130000:
                            tipo = 'BIGINT'
                        conn.execute(text(f'ALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS {columna} {tipo}'))
                indices = {n for (n,) in conn.execute(text(
                    "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()")).all()}
                if 'ix_events_source_id' not in indices:
                    conn.execute(text('CREATE INDEX IF NOT EXISTS ix_events_source_id ON events (source_id)'))
                if 'ix_links_event_id' not in indices:   # G5: la retracción dirigida busca por event_id
                    conn.execute(text('CREATE INDEX IF NOT EXISTS ix_links_event_id ON links (event_id)'))

            # Paso 1 de INFRA_OPERATIVA: events append-only (disparador), contador de versión del grafo,
            # bitácora de vistas, DEFAULT de txid/seq e índice parcial. Idempotente y nunca lanza.
            try:
                from core import ledger_ddl
                ledger_ddl.ensure_all(engine)
            except Exception as e:  # noqa: BLE001
                log.warning('init_schema: ledger_ddl no aplicado (%s)', type(e).__name__)
            try:   # un esquema re-creado (tests, re-migración) es otro linaje: las vistas lo releen
                from core.hotviews import signals as _hv_signals
                _hv_signals.on_schema_init()
            except Exception:  # noqa: BLE001
                pass
            try:   # paso 9: registro de gobernanza (artefactos del repo + release 1.0.0 si la base no tiene)
                from core import governance as _gov
                _gov.bootstrap_db(engine)
            except Exception as e:  # noqa: BLE001
                log.warning('init_schema: gobernanza no inicializada (%s)', type(e).__name__)

            if intento > 1:
                log.warning('init_schema: OK en el intento %d (la base tardó en arrancar)', intento)
            return True
        except Exception as e:  # noqa: BLE001
            ultimo = e
            if intento < retries:
                # Arranque en paralelo: la base suele estar lista en segundos.
                _time.sleep(delay * intento)

    log.error('init_schema falló tras %d intentos (la app sigue, la ontología no): %s',
              retries, ultimo)
    return False
