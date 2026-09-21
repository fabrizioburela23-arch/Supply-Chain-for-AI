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


def init_schema():
    """Crea las tablas si no existen (idempotente). Se llama al arrancar el
    server si ontology_available() y también desde el script de migración."""
    from sqlalchemy import text
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.create_all(engine)

    # Nunca debe impedir el arranque: si un ALTER falla, la app sigue y el
    # fallo se ve en los logs (mismo criterio que el resto de la ontología).
    with engine.begin() as conn:
        for tabla, columna, tipo in _COLUMNAS_TARDIAS:
            try:
                conn.execute(text(
                    f'ALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS {columna} {tipo}'))
            except Exception as e:  # noqa: BLE001
                log.warning('no se pudo añadir %s.%s (%s): %s', tabla, columna, tipo, e)
    with engine.begin() as conn:
        try:
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_events_source_id ON events (source_id)'))
        except Exception as e:  # noqa: BLE001
            log.warning('no se pudo crear ix_events_source_id: %s', e)
