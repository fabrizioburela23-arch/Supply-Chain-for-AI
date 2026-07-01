"""ontology/db.py — conexión a Postgres (fuente única de verdad de la ontología).

Sigue el mismo patrón de "feature opcional" que Neo4j (server.py:_temporal_mode):
si DATABASE_URL no está configurada, la ontología queda inactiva sin romper
el resto de la app. Railway inyecta DATABASE_URL automáticamente al añadir
el plugin de Postgres al proyecto.
"""
import os
from contextlib import contextmanager

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


def init_schema():
    """Crea las tablas si no existen (idempotente). Se llama al arrancar el
    server si ontology_available() y también desde el script de migración."""
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.create_all(engine)
