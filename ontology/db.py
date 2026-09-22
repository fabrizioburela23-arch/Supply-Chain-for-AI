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


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        url = DATABASE_URL
        # Railway a veces entrega postgres:// (esquema viejo); SQLAlchemy 1.4+/2.x
        # requiere postgresql://
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        _engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)
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
)


def schema_outdated(engine=None):
    """¿Falta alguna de las columnas tardías? Permite detectar una base con el
    esquema viejo SIN tener que provocar el error en una consulta real."""
    from sqlalchemy import inspect
    try:
        insp = inspect(engine or _get_engine())
        existentes = set(insp.get_table_names())
        faltan = []
        for tabla, columna, _tipo in _COLUMNAS_TARDIAS:
            if tabla not in existentes:
                continue          # la tabla aún no existe: create_all la hará completa
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

    ultimo = None
    for intento in range(1, max(1, retries) + 1):
        try:
            engine = _get_engine()
            Base.metadata.create_all(engine)

            with engine.begin() as conn:
                for tabla, columna, tipo in _COLUMNAS_TARDIAS:
                    conn.execute(text(
                        f'ALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS {columna} {tipo}'))
                conn.execute(text(
                    'CREATE INDEX IF NOT EXISTS ix_events_source_id ON events (source_id)'))

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
