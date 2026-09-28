"""research/models.py — tablas de la capa DERIVED CLAIMS (Phase 2).

Viven en el MISMO Base que la ontología (init_schema las crea), pero son
tablas propias: un agente escribe aquí y SOLO aquí. Los hechos del grafo
(`events`/`objects`/`links`) y los datos de mercado nunca se reescriben desde
un agente — una claim es una conclusión derivada, no un hecho.
"""
import uuid

from sqlalchemy import (Column, DateTime, Float, Index, Integer, String, Text, func)
from sqlalchemy.dialects.postgresql import JSONB

from ontology.models import Base

HORIZONS = ('INTRADAY', 'SHORT_TERM', 'MEDIUM_TERM', 'LONG_TERM', 'STRUCTURAL')
DEPTHS = ('QUICK', 'STANDARD', 'DEEP')
STANCES = ('positive', 'negative', 'neutral', 'mixed')
CLAIM_STATUSES = ('active', 'superseded', 'retracted')


def _uuid():
    return str(uuid.uuid4())


class ResearchClaim(Base):
    """Conclusión DERIVADA de un agente sobre una entidad.

    Responde siempre: quién (agent_id/version/model/prompt_version), cuándo
    (created_at + valid_from/valid_to), con qué evidencia (research_evidence),
    qué afecta (affected_entity_ids), qué horizonte, qué confianza (con sus
    componentes) y qué la refutaría (falsifiers)."""
    __tablename__ = 'research_claims'

    id = Column(String(40), primary_key=True, default=_uuid)
    job_id = Column(String(40), nullable=True, index=True)
    run_id = Column(String(40), nullable=True, index=True)
    agent_id = Column(String(60), nullable=False, index=True)
    agent_type = Column(String(40), nullable=False, index=True)
    agent_version = Column(String(20), nullable=False)
    subject_entity_id = Column(String(120), nullable=False, index=True)
    predicate = Column(String(80), nullable=False)       # p.ej. MAY_FACE_MARGIN_PRESSURE
    object = Column(String(300), nullable=True)          # p.ej. "next_2_quarters" / texto corto
    claim_type = Column(String(30), nullable=False)      # observation / risk / opportunity / forecast
    topic = Column(String(40), nullable=False, index=True)  # margins / demand / … (vocabulario cerrado)
    stance = Column(String(12), nullable=False)          # positive / negative / neutral / mixed
    statement_es = Column(Text, nullable=False)
    statement_en = Column(Text, nullable=True)
    reasoning_summary = Column(Text, nullable=True)      # resumen AUDITABLE (no chain-of-thought)
    horizon = Column(String(16), nullable=False, index=True)
    depth = Column(String(10), nullable=False)
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_to = Column(DateTime(timezone=True), nullable=True)
    confidence = Column(Float, nullable=False)
    confidence_components = Column(JSONB, nullable=False, default=dict)
    affected_entity_ids = Column(JSONB, nullable=False, default=list)
    falsifiers = Column(JSONB, nullable=False, default=list)     # qué la demostraría incorrecta
    status = Column(String(12), nullable=False, default='active', index=True)
    model = Column(String(80), nullable=True)
    prompt_version = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    __table_args__ = (
        Index('ix_claims_subject_horizon', 'subject_entity_id', 'horizon', 'status'),
    )


class ResearchEvidence(Base):
    """Evidencia de una claim — a favor (supporting) o en contra (counter).
    Apunta a una Source de la ontología (source_id) cuando hay URL, o a una
    referencia interna reproducible (p.ej. 'yahoo:fundamentals:NVDA')."""
    __tablename__ = 'research_evidence'

    id = Column(String(40), primary_key=True, default=_uuid)
    claim_id = Column(String(40), nullable=False, index=True)
    stance = Column(String(10), nullable=False)          # supporting / counter
    context_ref = Column(String(10), nullable=True)      # E1..En del paquete de evidencia
    source_id = Column(String(120), nullable=True, index=True)
    source_type = Column(String(30), nullable=False)     # financials / market / news / catalog / web / graph
    source_reference = Column(Text, nullable=True)       # URL o referencia interna
    title = Column(Text, nullable=True)
    excerpt = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), nullable=True)
    relevance = Column(Float, nullable=True)
    reliability = Column(Float, nullable=True)           # 0-1 (de la confiabilidad de la fuente)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ClaimRelation(Base):
    """Relación entre claims. Phase 2 solo crea POTENTIALLY_CONTRADICTS: se
    DETECTA la tensión, no se decide quién tiene razón (eso es Phase 3)."""
    __tablename__ = 'claim_relations'

    id = Column(String(40), primary_key=True, default=_uuid)
    claim_a = Column(String(40), nullable=False, index=True)
    claim_b = Column(String(40), nullable=False, index=True)
    rel_type = Column(String(40), nullable=False, default='POTENTIALLY_CONTRADICTS')
    reason = Column(Text, nullable=True)
    detector = Column(String(40), nullable=False, default='rule:stance-topic-horizon')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AgentRun(Base):
    """Observabilidad: UNA ejecución de UN agente. Permite responder "¿por
    qué el sistema llegó a esta conclusión?" — con qué modelo, por qué se
    disparó, con qué contexto, cuánto costó y qué produjo."""
    __tablename__ = 'agent_runs'

    id = Column(String(40), primary_key=True, default=_uuid)
    job_id = Column(String(40), nullable=True, index=True)
    agent_id = Column(String(60), nullable=False, index=True)
    agent_type = Column(String(40), nullable=False)
    entity_id = Column(String(120), nullable=True, index=True)
    trigger = Column(JSONB, nullable=False, default=dict)          # {kind:'user'|'event', ref, by}
    depth = Column(String(10), nullable=False)
    status = Column(String(16), nullable=False, default='running', index=True)  # running/done/failed/skipped
    model = Column(String(80), nullable=True)
    provider = Column(String(30), nullable=True)
    context_refs = Column(JSONB, nullable=False, default=list)     # [{ref, source_type, reference}]
    tools_used = Column(JSONB, nullable=False, default=list)
    tokens_in = Column(Integer, nullable=True)                     # estimados (chars/4)
    tokens_out = Column(Integer, nullable=True)
    est_cost_usd = Column(Float, nullable=True)
    claims_generated = Column(Integer, nullable=False, default=0)
    validation = Column(JSONB, nullable=False, default=dict)       # attempts / repaired / rejected
    errors = Column(JSONB, nullable=False, default=list)
    summary = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    latency_ms = Column(Integer, nullable=True)


class ResearchJob(Base):
    """Un pedido de investigación (del usuario o de un evento) sobre una entidad."""
    __tablename__ = 'research_jobs'

    id = Column(String(40), primary_key=True, default=_uuid)
    entity_id = Column(String(120), nullable=False, index=True)
    depth = Column(String(10), nullable=False)
    trigger = Column(JSONB, nullable=False, default=dict)
    requested_by = Column(String(120), nullable=True)
    agents = Column(JSONB, nullable=False, default=list)
    status = Column(String(16), nullable=False, default='queued', index=True)  # queued/running/done/failed
    synthesis = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    dedupe_key = Column(String(200), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
