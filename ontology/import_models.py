"""ontology/import_models.py — tablas del importador de fichas khipus.company/1 (E2.3), APPEND-ONLY.

  import_files          archivos subidos por sha256 (JSONL comprimido): la corrida cita el archivo, nunca lo pierde
  import_runs           una fila por corrida aplicada o deshecha: lote, huella del plan (plan_sha), decisión del libro,
                        versión del grafo antes/después y el resumen (qué se creó/fusionó/actualizó/omitió)
  import_pending_links  vínculos cuya contraparte todavía no existe en el grafo (ni en el lote): quedan a la espera
                        de que llegue la ficha de la otra parte; se resuelven en una corrida posterior

Mismo `Base` que la ontología. Como `init_schema` no conoce este módulo, `ensure_tables(engine)` las crea (solo si
faltan) y les pone el disparador `kh_append_only` (core/ledger_ddl.ensure_append_only): nunca UPDATE/DELETE; una
corrección es otra fila (otra corrida). Pendiente de registro central: añadir `ontology.import_models` a
ontology/models.py y las tres tablas a core/ledger_ddl.APPEND_ONLY_TABLES (lo hace el integrador).
"""
import logging
import threading

from sqlalchemy import CHAR, Column, DateTime, Integer, LargeBinary, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ontology.models import Base

log = logging.getLogger('khipu')
_NOW = text('clock_timestamp()')
IMPORT_TABLES = ('import_files', 'import_runs', 'import_pending_links')
_READY = {'engine': None}
_LOCK = threading.Lock()


class ImportFile(Base):
    __tablename__ = 'import_files'
    sha256 = Column(CHAR(64), primary_key=True)             # sha del contenido SIN comprimir (lo que subió la persona)
    name = Column(String(200), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    n_records = Column(Integer, nullable=True)
    content_type = Column(String(40), nullable=False)        # jsonl | json
    content = Column(LargeBinary, nullable=False)            # zlib del contenido
    uploaded_by = Column(String(96), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=_NOW)


class ImportRun(Base):
    __tablename__ = 'import_runs'
    id = Column(UUID(as_uuid=True), primary_key=True)
    kind = Column(String(12), nullable=False)                # apply | rollback
    batch = Column(String(60), nullable=True)
    source_channel = Column(String(60), nullable=False)      # Event.source de sus eventos: import:<run_id>
    file_sha = Column(CHAR(64), nullable=True)
    plan_sha = Column(CHAR(64), nullable=True)
    decision_id = Column(UUID(as_uuid=True), nullable=True)
    principal_id = Column(String(96), nullable=False)
    status = Column(String(16), nullable=False)              # applied | rolled_back
    rolled_back_run = Column(UUID(as_uuid=True), nullable=True)   # en un rollback: la corrida que deshace
    graph_version_before = Column(Integer, nullable=True)
    graph_version_after = Column(Integer, nullable=True)
    summary = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=_NOW)


class ImportPendingLink(Base):
    __tablename__ = 'import_pending_links'
    id = Column(UUID(as_uuid=True), primary_key=True)
    run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    record_id = Column(String(80), nullable=False)
    relation_id = Column(String(40), nullable=False)
    company_id = Column(String(120), nullable=False)         # la empresa de la ficha (ya en el grafo)
    counterparty = Column(JSONB, nullable=False)             # nombre + identificadores que trajo la ficha
    payload = Column(JSONB, nullable=False)                  # el vínculo listo para escribir cuando exista la otra parte
    reason = Column(String(40), nullable=False)              # counterparty_unknown
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=_NOW)


def ensure_tables(engine=None):
    """Crea las tres tablas si faltan y les pone el disparador append-only. Idempotente; una vez por engine."""
    from ontology.db import _get_engine
    engine = engine or _get_engine()
    with _LOCK:
        if _READY['engine'] is engine:
            return True
        try:
            Base.metadata.create_all(engine, tables=[ImportFile.__table__, ImportRun.__table__,
                                                     ImportPendingLink.__table__])
            from core import ledger_ddl
            with engine.begin() as conn:
                ledger_ddl.ensure_append_only(conn, tables=IMPORT_TABLES)
            _READY['engine'] = engine
            return True
        except Exception as e:  # noqa: BLE001 — sin tablas no hay importación (el llamador responde 503)
            log.warning('import_models: no se pudieron preparar las tablas (%s)', type(e).__name__)
            return False


def _reset_for_tests():
    with _LOCK:
        _READY['engine'] = None
