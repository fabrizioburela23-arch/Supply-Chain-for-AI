"""ontology/models.py — esquema SQLAlchemy de la ontología.

Diseño (Fase 1 de ROADMAP_KHIPUS_ONTOLOGIA.md, adaptado a Flask/SQLAlchemy):

- `events`: tabla INMUTABLE append-only. Es la fuente única de verdad.
  Cada evento lleva `valid_from`/`valid_to` (cuándo es cierto EN EL MUNDO —
  tiempo de validez) y `recorded_at` (cuándo lo supimos — tiempo de sistema).
  Un `as_of` en la API consulta tiempo de VALIDEZ (igual que el Grafo Temporal
  ya construido en el cliente: qué relaciones estaban vigentes en tal fecha).

- `objects` / `links`: vistas MATERIALIZADAS de "estado actual" (conocimiento
  más reciente). Se actualizan al aplicar cada evento (no se recalculan desde
  cero en cada request) — esto es lo que consultan la mayoría de endpoints de
  lectura. Para time-travel (`as_of`) SÍ se consulta `events` directamente,
  reconstruyendo qué estaba vigente en esa fecha.
"""
import enum
import uuid

from sqlalchemy import (
    Column, String, Text, DateTime, Float, Boolean, Index, ForeignKey, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class EventType(str, enum.Enum):
    OBJECT_CREATED = 'ObjectCreated'
    OBJECT_UPDATED = 'ObjectUpdated'
    LINK_CREATED = 'LinkCreated'
    LINK_REMOVED = 'LinkRemoved'
    PRICE_OBSERVED = 'PriceObserved'
    ACTION_EXECUTED = 'ActionExecuted'  # reservado para Fase 2 (Acciones)


class Event(Base):
    """Tabla append-only. NUNCA se hace UPDATE/DELETE sobre filas existentes —
    una corrección es un evento nuevo con su propio valid_from."""
    __tablename__ = 'events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(40), nullable=False, index=True)
    object_id = Column(String(120), nullable=True, index=True)   # objeto principal del evento
    target_id = Column(String(120), nullable=True, index=True)   # para links: el otro extremo
    payload = Column(JSONB, nullable=False, default=dict)
    valid_from = Column(DateTime(timezone=True), nullable=False, index=True)
    valid_to = Column(DateTime(timezone=True), nullable=True, index=True)  # NULL = sigue vigente
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    source = Column(String(60), nullable=False)     # 'manual', 'migration_v0', 'gdelt', 'marketstack'…
    actor = Column(String(120), nullable=False)      # usuario o agente

    __table_args__ = (
        Index('ix_events_object_validity', 'object_id', 'valid_from', 'valid_to'),
    )


class ObjectRecord(Base):
    """Estado materializado ACTUAL de un objeto (empresa, tecnología, política…).
    `properties` acumula el último valor conocido de cada campo."""
    __tablename__ = 'objects'

    id = Column(String(120), primary_key=True)
    type = Column(String(40), nullable=False, index=True)   # Company, Tech, Policy, Country…
    label = Column(String(300), nullable=False)
    properties = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class LinkRecord(Base):
    """Vínculo materializado. `valid_to IS NULL` = vigente ahora mismo (según
    el conocimiento más reciente). Varias filas pueden existir para el mismo
    par (source,target,rel_type) representando distintas ventanas de validez
    a lo largo del tiempo (ej. Qualcomm→Huawei 2019-2021)."""
    __tablename__ = 'links'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(String(120), ForeignKey('objects.id'), nullable=False, index=True)
    target_id = Column(String(120), ForeignKey('objects.id'), nullable=False, index=True)
    rel_type = Column(String(40), nullable=False, index=True)   # supply, fabrica, sanciona, depende…
    weight = Column(Float, nullable=True)
    properties = Column(JSONB, nullable=False, default=dict)    # headline, confidence, source…
    valid_from = Column(DateTime(timezone=True), nullable=False, index=True)
    valid_to = Column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index('ix_links_pair', 'source_id', 'target_id', 'rel_type'),
        Index('ix_links_validity', 'valid_from', 'valid_to'),
    )
