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
CLAIM_STATUSES = ('active', 'superseded', 'retracted', 'falsified')   # falsified: C8 (regla verificable disparada)


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
    falsifier_rules = Column(JSONB, nullable=True)               # C8: [{metric, op, threshold, by}] verificables
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


# ════════════════════════════════════════════════════════════════════════════
# PHASE 3 — aprendizaje (resultados + calibración) y comité de inversión.
# Tablas NUEVAS; no cambian ninguna columna de Phase 2. Todas append-only o
# con auditoría: una evaluación nunca se reescribe, un memo guarda su historia.
# ════════════════════════════════════════════════════════════════════════════
from sqlalchemy import Boolean, UniqueConstraint  # noqa: E402

OUTCOME_RESULTS = ('hit', 'miss', 'n/a')
MEMO_STATUSES = ('running', 'failed', 'proposed', 'approved', 'rejected', 'executed')
DECISIONS = ('BUY', 'ADD', 'HOLD', 'TRIM', 'SELL', 'AVOID')


class ClaimBaseline(Base):
    """Foto de partida de una claim (una por claim): con qué precio y en qué
    fecha se hizo la predicción, contra qué referencia (SPY) y cuándo se
    califica (checkpoints). Se crea al persistir la claim (runner) o, para
    claims anteriores a Phase 3, en la primera evaluación (backfill)."""
    __tablename__ = 'claim_baselines'

    id = Column(String(40), primary_key=True, default=_uuid)
    claim_id = Column(String(40), nullable=False, unique=True, index=True)
    entity_id = Column(String(120), nullable=False, index=True)
    agent_type = Column(String(40), nullable=False, index=True)
    stance = Column(String(12), nullable=False)
    horizon = Column(String(16), nullable=False)
    confidence = Column(Float, nullable=False)                  # confianza calculada (conf-v1) al crearla
    calibrated_confidence = Column(Float, nullable=True)        # la calibrada vigente en ese momento
    symbol = Column(String(20), nullable=True)                  # ticker si cotiza
    scoreable = Column(Boolean, nullable=False, default=True)
    na_reason = Column(Text, nullable=True)                     # por qué NO se califica (mixta, no cotiza…)
    baseline_date = Column(String(10), nullable=False)          # fecha de mercado (Nueva York) de la predicción
    baseline_price = Column(Float, nullable=True)               # precio EN VIVO al crearla (auditoría)
    baseline_currency = Column(String(8), nullable=True)
    baseline_source = Column(String(40), nullable=True)
    benchmark_symbol = Column(String(12), nullable=False, default='SPY')
    benchmark_price = Column(Float, nullable=True)              # SPY en vivo al crearla (auditoría)
    band = Column(Float, nullable=False, default=0.02)
    checkpoints = Column(JSONB, nullable=False, default=list)   # [{label, days, due_date, final}]
    claim_created_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ClaimOutcome(Base):
    """UNA evaluación de UN checkpoint de una claim (append-only, idempotente
    por (claim_id, checkpoint)). Guarda los precios usados y la cuenta."""
    __tablename__ = 'claim_outcomes'

    id = Column(String(40), primary_key=True, default=_uuid)
    claim_id = Column(String(40), nullable=False, index=True)
    baseline_id = Column(String(40), nullable=True)
    entity_id = Column(String(120), nullable=False, index=True)
    agent_type = Column(String(40), nullable=False, index=True)
    horizon = Column(String(16), nullable=False)
    stance = Column(String(12), nullable=False)
    confidence = Column(Float, nullable=False)
    checkpoint = Column(String(24), nullable=False)             # p.ej. interim_7d / final_30d
    checkpoint_days = Column(Integer, nullable=False)
    final = Column(Boolean, nullable=False, default=False)
    due_date = Column(String(10), nullable=False)
    symbol = Column(String(20), nullable=True)
    base_date = Column(String(10), nullable=True)
    base_price = Column(Float, nullable=True)                   # cierre AJUSTADO (misma serie que eval)
    eval_date = Column(String(10), nullable=True)
    eval_price = Column(Float, nullable=True)
    bench_base_price = Column(Float, nullable=True)
    bench_eval_price = Column(Float, nullable=True)
    asset_return = Column(Float, nullable=True)
    bench_return = Column(Float, nullable=True)
    excess_return = Column(Float, nullable=True)
    band = Column(Float, nullable=False, default=0.02)
    result = Column(String(4), nullable=False)                  # hit / miss / n/a
    reason = Column(Text, nullable=True)
    reason_en = Column(Text, nullable=True)                     # la misma cuenta en inglés (UI bilingüe)
    claim_status = Column(String(12), nullable=True)            # active/superseded/retracted al evaluar
    price_source = Column(String(60), nullable=True)
    method = Column(String(20), nullable=False, default='outcome-v1')
    evaluated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    __table_args__ = (UniqueConstraint('claim_id', 'checkpoint', name='uq_outcome_claim_checkpoint'),)


class CalibrationSnapshot(Base):
    """Foto periódica del historial (track record) por agente — para ver cómo
    evoluciona la calibración en el tiempo. agent_type NULL = global."""
    __tablename__ = 'calibration_snapshots'

    id = Column(String(40), primary_key=True, default=_uuid)
    as_of = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    agent_type = Column(String(40), nullable=True, index=True)
    n_scored = Column(Integer, nullable=False, default=0)
    hits = Column(Integer, nullable=False, default=0)
    hit_rate = Column(Float, nullable=True)
    brier = Column(Float, nullable=True)
    reliability = Column(Float, nullable=True)
    buckets = Column(JSONB, nullable=False, default=list)
    method = Column(String(20), nullable=False, default='cal-v1')


class CommitteeMemo(Base):
    """Memo del COMITÉ DE INVERSIÓN automatizado: decisión propuesta + tamaño
    (determinista) + tesis/riesgos/disenso (presidente IA o plantilla sin IA).
    Una propuesta: NUNCA se ejecuta sin aprobación humana (docs/PHASE3.md)."""
    __tablename__ = 'committee_memos'

    id = Column(String(40), primary_key=True, default=_uuid)
    entity_id = Column(String(120), nullable=False, index=True)
    symbol = Column(String(20), nullable=True)
    client_id = Column(String(60), nullable=True, index=True)
    requested_by = Column(String(120), nullable=False)
    status = Column(String(12), nullable=False, default='proposed', index=True)
    decision = Column(String(8), nullable=True)
    quant_decision = Column(String(8), nullable=True)           # la del núcleo determinista
    overall_conviction = Column(Float, nullable=True)           # −100..+100
    conviction = Column(JSONB, nullable=False, default=dict)    # por horizonte (con sus componentes)
    sizing = Column(JSONB, nullable=False, default=dict)        # cuenta del tamaño (vol-targeting)
    memo = Column(JSONB, nullable=False, default=dict)          # tesis, riesgos, disenso, falsadores…
    inputs = Column(JSONB, nullable=False, default=dict)        # paquete de evidencia (auditoría)
    ai_used = Column(Boolean, nullable=False, default=False)
    model = Column(String(80), nullable=True)
    provider = Column(String(60), nullable=True)
    validation = Column(JSONB, nullable=False, default=dict)
    disclaimer_es = Column(Text, nullable=True)
    disclaimer_en = Column(Text, nullable=True)
    preview_id = Column(String(60), nullable=True)
    preview = Column(JSONB, nullable=True)
    decided_by = Column(String(120), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_note = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    error_en = Column(Text, nullable=True)
    audit = Column(JSONB, nullable=False, default=list)         # [{at, actor, action, detail}]
    method = Column(String(20), nullable=False, default='committee-v1')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


# ════════════════════════════════════════════════════════════════════════════
# GASTO DE IA (2026-10-02, pedido: "saber cuánto gasto, de dónde y controlarlo")
# Un registro por llamada a un proveedor de IA (core/ai_usage.py lo escribe en
# lotes, sin frenar la llamada) + ajustes editables con PIN (límites).
# ════════════════════════════════════════════════════════════════════════════
class DecisionShadow(Base):
    """JEV (core/decide.py) en MODO SOMBRA: lo que decidió vs lo que hizo el
    sistema, para medir acuerdo antes de darle control por función."""
    __tablename__ = 'decision_shadow'

    id = Column(Integer, primary_key=True, autoincrement=True)
    at = Column(DateTime(timezone=True), nullable=False, index=True)
    feature = Column(String(40), nullable=False, index=True)
    key = Column(String(200), nullable=True)
    decision = Column(JSONB, nullable=False, default=dict)
    actual = Column(JSONB, nullable=False, default=dict)
    agree = Column(Boolean, nullable=True)


class AIUsage(Base):
    __tablename__ = 'ai_usage'

    id = Column(Integer, primary_key=True, autoincrement=True)
    at = Column(DateTime(timezone=True), nullable=False, index=True)
    provider = Column(String(20), nullable=False, index=True)       # claude | gemini | nvidia
    model = Column(String(80), nullable=True)
    feature = Column(String(40), nullable=False, index=True)        # khipu_chat, comite, investigacion…
    who = Column(String(120), nullable=True, index=True)            # usuario/cliente que lo pidió
    tokens_in = Column(Integer, nullable=False, default=0)
    tokens_out = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    estimated = Column(Boolean, nullable=False, default=False)      # tokens estimados (proveedor no los dio)
    ok = Column(Boolean, nullable=False, default=True)
    ms = Column(Integer, nullable=True)


class AISetting(Base):
    __tablename__ = 'ai_settings'

    key = Column(String(60), primary_key=True)
    value = Column(JSONB, nullable=False, default=dict)
    updated_by = Column(String(120), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


# ════════════════════════════════════════════════════════════════════════════
# REPORTES DE CARTERA (2026-10-03, pedido: "reportes diarios, mensuales o a
# pedido en base a tus carteras en relación con tu posición inicial")
# El dueño se identifica por una llave aleatoria del navegador (solo se guarda
# su hash): nadie más puede leer tus reportes ni tu cartera.
# ════════════════════════════════════════════════════════════════════════════
class PortfolioWatch(Base):
    __tablename__ = 'portfolio_watches'

    id = Column(String(40), primary_key=True, default=_uuid)
    owner_hash = Column(String(64), nullable=False, index=True)
    owner_name = Column(String(120), nullable=True)
    source_key = Column(String(80), nullable=False)              # market | pf:<id> | broker
    name = Column(String(160), nullable=False)
    positions = Column(JSONB, nullable=False, default=list)      # [{id, symbol, label, shares, cost_usd}]
    start_value_usd = Column(Float, nullable=True)
    start_date = Column(String(10), nullable=True)
    cash_usd = Column(Float, nullable=False, default=0.0)
    profile = Column(JSONB, nullable=False, default=dict)
    schedule = Column(String(10), nullable=False, default='off')  # off | daily | weekly | monthly
    last_report_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)


class PortfolioReport(Base):
    __tablename__ = 'portfolio_reports'

    id = Column(String(40), primary_key=True, default=_uuid)
    owner_hash = Column(String(64), nullable=False, index=True)
    watch_id = Column(String(40), nullable=True, index=True)
    kind = Column(String(10), nullable=False, default='manual')  # manual | daily | weekly | monthly
    title = Column(String(200), nullable=False)
    period_from = Column(String(10), nullable=True)
    period_to = Column(String(10), nullable=True)
    summary = Column(Text, nullable=True)
    data = Column(JSONB, nullable=False, default=dict)
    read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class UserState(Base):
    """Sincronización entre dispositivos (2026-10-03): carteras, perfil y posiciones
    del usuario, por dueño (hash de la llave del navegador). Último que escribe gana."""
    __tablename__ = 'user_state'

    owner_hash = Column(String(64), primary_key=True)
    key = Column(String(40), primary_key=True)
    value = Column(JSONB, nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False)
