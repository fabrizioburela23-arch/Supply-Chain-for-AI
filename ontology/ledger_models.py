"""ontology/ledger_models.py — el LIBRO DE DECISIONES (docs/INFRA_OPERATIVA.md §2.1; paso 6 del plan).

Una decisión es una FILA de este libro, no un nodo del grafo (ARQ §2.2 regla 5, §3.4, §19.1). Tablas, sobre
el mismo `Base` de la ontología para que `init_schema` (create_all) las cree y las pruebas las limpien:

  decision_blobs      contenido direccionado por hash (json canónico comprimido); purga por retención = body NULL
  decisions           la ficha: quién (principal tipado), qué (kind/status/subject), cuándo (valid_at, recorded_at,
                      txid), con qué conocimiento (graph_version, release_hash, code_sha, lineage_id, manifest)
  decision_refs       evidencia, efectos, vistas, política, causa — se añaden también DESPUÉS (solo INSERT)
  decision_outcomes   resultado posterior; el vigente es el último (nunca se pisa)
  decision_violations índice consultable de los veredictos de las puertas (paso 10+)
  ledger_seals        UNA cadena de hashes sobre events, kh_tx_versions, decisions, refs, outcomes y broker_audit
  ledger_meta         linaje (cluster_id + primer txid): detecta restauraciones de la base
  ledger_anchors      ancla diaria (paso 7): cabeza de la cadena por día; GET /api/ledger/anchor la publica y el
                      GitHub Action smoke-mcp.yml la guarda FUERA de la base (artefacto + resumen del run)

Todas (salvo blobs, que tienen su guardia de purga) son APPEND-ONLY en la base: core/ledger_ddl les pone
`kh_append_only()`. Los índices especiales (GIN de subject, únicos parciales con expresión) y los disparadores
también viven en core/ledger_ddl.

`txid` usa el tipo xid8 + DEFAULT pg_current_xact_id() desde Postgres 13 (Railway usa 16); en una base más
vieja se compila como bigint + txid_current() (core/ledger_ddl.detect_xid8 corre ANTES de create_all).
"""
from sqlalchemy import (
    CHAR, BigInteger, Boolean, CheckConstraint, Column, Date, DateTime, Float, ForeignKey, Identity, Index, Integer,
    LargeBinary, PrimaryKeyConstraint, SmallInteger, String, Text, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement
from sqlalchemy.types import UserDefinedType

from ontology.models import Base


class XID8(UserDefinedType):
    """xid8 (o bigint en Postgres < 13). Solo DDL: el código lo escribe por DEFAULT y lo lee como texto."""
    cache_ok = True

    def get_col_spec(self, **kw):
        from core import ledger_ddl
        return ledger_ddl._txid_type()


class txid_default(FunctionElement):      # noqa: N801 — se usa como valor de server_default
    """DEFAULT pg_current_xact_id() (o txid_current()) según la base."""
    inherit_cache = True


@compiles(txid_default)
def _compile_txid_default(element, compiler, **kw):
    from core import ledger_ddl
    return ledger_ddl.txid_expr()


_NOW = text('clock_timestamp()')

DECISION_STATUSES = ('proposed', 'pending_approval', 'approved', 'rejected', 'blocked', 'executed', 'failed',
                     'noop', 'answered', 'fired', 'recorded', 'expired')
PRINCIPAL_KINDS = ('human', 'agent', 'system', 'external_ai')
AUTHS = ('pin', 'mcp_token', 'oauth', 'agent_registry', 'scheduler', 'none')
REF_ROLES = ('evidence', 'effect', 'input', 'view', 'policy', 'cause')
OUTCOME_KINDS = ('order_status', 'fill', 'claim_eval', 'alert_ack', 'user_feedback', 'replay', 'expired', 'error',
                 'reverted', 'agree')
SEVERITIES = ('block', 'requires_approval', 'warn', 'info')
RETENTION = ('legal', 'standard_90d')


def _in(col, values):
    return f"{col} IN ({', '.join(repr(v) for v in values)})"


class DecisionBlob(Base):
    __tablename__ = 'decision_blobs'
    sha256 = Column(CHAR(64), primary_key=True)              # sha de los bytes canónicos SIN comprimir
    kind = Column(String(24), nullable=False)                # inputs|output|payload|account_snapshot|plan|focus|…
    body = Column(LargeBinary, nullable=True)                # json canónico con zlib; NULL solo tras purga
    size_bytes = Column(Integer, nullable=False)
    retention_class = Column(String(16), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=_NOW)
    purged_at = Column(DateTime(timezone=True), nullable=True)
    purge_decision_id = Column(UUID(as_uuid=True), nullable=True)
    __table_args__ = (CheckConstraint(_in('retention_class', RETENTION), name='ck_blob_retention'),)


class Decision(Base):
    __tablename__ = 'decisions'
    id = Column(UUID(as_uuid=True), primary_key=True)        # se reserva al ENTRAR en decision_scope
    seq = Column(BigInteger, Identity(always=True), nullable=False, unique=True)
    kind = Column(String(48), nullable=False)
    kind_version = Column(SmallInteger, nullable=False, server_default=text('1'))
    durability = Column(String(5), nullable=False)
    status = Column(String(16), nullable=False)
    # DEFERRABLE: una decisión hija (scope anidado) se escribe ANTES que su padre en la MISMA transacción;
    # la FK se comprueba al confirmar.
    parent_id = Column(UUID(as_uuid=True), ForeignKey('decisions.id', deferrable=True, initially='DEFERRED'),
                       nullable=True)
    supersedes_id = Column(UUID(as_uuid=True), ForeignKey('decisions.id', deferrable=True, initially='DEFERRED'),
                           nullable=True)
    correlation_id = Column(String(64), nullable=True)
    principal_id = Column(String(96), nullable=False)
    principal_kind = Column(String(12), nullable=False)
    auth = Column(String(16), nullable=False)
    channel = Column(String(12), nullable=False)
    declared_name = Column(String(80), nullable=True)        # SOLO informativo (lo que escribió el cliente)
    on_behalf_of = Column(String(96), nullable=True)         # client_id u owner_hash
    subject = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    valid_at = Column(DateTime(timezone=True), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=_NOW)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    txid = Column(XID8(), nullable=False, server_default=txid_default())
    lineage_id = Column(UUID(as_uuid=True), nullable=False)
    graph_version = Column(BigInteger, nullable=True)
    known_snapshot = Column(Text, nullable=True)             # pg_snapshot como texto (opcional)
    release_hash = Column(CHAR(64), nullable=False)
    code_sha = Column(String(40), nullable=False)
    manifest = Column(JSONB, nullable=False)
    manifest_sha = Column(CHAR(64), nullable=False)
    inputs_sha = Column(CHAR(64), ForeignKey('decision_blobs.sha256'), nullable=True)
    output = Column(JSONB, nullable=True)
    output_sha = Column(CHAR(64), nullable=True)
    verdict = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    model = Column(JSONB, nullable=True)
    __table_args__ = (
        CheckConstraint(r"kind ~ '^[a-z_]+(\.[a-z_]+)+$'", name='ck_dec_kind'),
        CheckConstraint(_in('durability', ('sync', 'async')), name='ck_dec_durability'),
        CheckConstraint(_in('status', DECISION_STATUSES), name='ck_dec_status'),
        CheckConstraint(_in('principal_kind', PRINCIPAL_KINDS), name='ck_dec_principal_kind'),
        CheckConstraint(_in('auth', AUTHS), name='ck_dec_auth'),
        Index('ix_dec_kind_time', 'kind', text('recorded_at DESC')),
        Index('ix_dec_principal', 'principal_id', text('recorded_at DESC')),
        Index('ix_dec_txid', 'txid'),
    )


class DecisionRef(Base):
    __tablename__ = 'decision_refs'
    decision_id = Column(UUID(as_uuid=True), ForeignKey('decisions.id'), nullable=False)
    role = Column(String(10), nullable=False)
    ref_kind = Column(String(20), nullable=False)
    ref_id = Column(String(128), nullable=False)
    ref_hash = Column(CHAR(64), nullable=True)
    as_of = Column(DateTime(timezone=True), nullable=True)
    note = Column(JSONB, nullable=True)
    txid = Column(XID8(), nullable=False, server_default=txid_default())
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=_NOW)
    __table_args__ = (
        PrimaryKeyConstraint('decision_id', 'role', 'ref_kind', 'ref_id', name='pk_decision_refs'),
        CheckConstraint(_in('role', REF_ROLES), name='ck_dref_role'),
        Index('ix_dref_target', 'ref_kind', 'ref_id'),
        Index('ix_dref_txid', 'txid'),
    )


class DecisionOutcome(Base):
    __tablename__ = 'decision_outcomes'
    id = Column(BigInteger, Identity(always=True), primary_key=True)
    decision_id = Column(UUID(as_uuid=True), ForeignKey('decisions.id'), nullable=False)
    outcome_kind = Column(String(20), nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(40), nullable=False)
    result = Column(JSONB, nullable=False)
    release_hash = Column(CHAR(64), nullable=False)
    txid = Column(XID8(), nullable=False, server_default=txid_default())
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=_NOW)
    __table_args__ = (
        CheckConstraint(_in('outcome_kind', OUTCOME_KINDS), name='ck_dout_kind'),
        Index('ix_dout_dec', 'decision_id', text('recorded_at DESC')),
    )


class DecisionViolation(Base):
    __tablename__ = 'decision_violations'
    decision_id = Column(UUID(as_uuid=True), ForeignKey('decisions.id'), nullable=False)
    ord = Column(SmallInteger, nullable=False)
    rule_iri = Column(String(96), nullable=False)
    severity = Column(String(18), nullable=False)
    focus = Column(String(128), nullable=False)
    value = Column(JSONB, nullable=True)
    shapes_hash = Column(CHAR(64), nullable=False)
    __table_args__ = (
        PrimaryKeyConstraint('decision_id', 'ord', name='pk_decision_violations'),
        CheckConstraint(_in('severity', SEVERITIES), name='ck_viol_severity'),
        Index('ix_viol_rule', 'rule_iri'),
    )


class LedgerSeal(Base):
    __tablename__ = 'ledger_seals'
    seal_no = Column(BigInteger, Identity(always=True), primary_key=True)
    row_table = Column(String(24), nullable=False)
    row_id = Column(String(64), nullable=False)
    row_sha = Column(CHAR(64), nullable=False)      # sha de la fila LEÍDA (to_jsonb → forma canónica)
    prev_hash = Column(CHAR(64), nullable=False)
    hash = Column(CHAR(64), nullable=False)         # sha256(prev_hash ‖ row_table ‖ row_id ‖ row_sha)
    sealed_at = Column(DateTime(timezone=True), nullable=False, server_default=_NOW)
    __table_args__ = (Index('ux_seal_row', 'row_table', 'row_id', unique=True),)


class LedgerMeta(Base):
    __tablename__ = 'ledger_meta'
    lineage_id = Column(UUID(as_uuid=True), primary_key=True)
    cluster_id = Column(BigInteger, nullable=False)
    first_txid = Column(XID8(), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=_NOW)
    note = Column(Text, nullable=True)


class LedgerAnchor(Base):
    """Ancla diaria (paso 7, §2.8): la cabeza de la cadena de sellos de ese día (UTC) en ese linaje, con el
    resultado de la verificación previa. Append-only. La copia EXTERNA (GitHub Actions) es la única defensa
    contra un superusuario que desactive los disparadores y reescriba todo de forma coherente."""
    __tablename__ = 'ledger_anchors'
    id = Column(BigInteger, Identity(always=True), primary_key=True)
    day = Column(Date, nullable=False)                      # día UTC (reloj de la base)
    head_seal = Column(BigInteger, nullable=False)
    head_hash = Column(CHAR(64), nullable=False)
    lineage_id = Column(UUID(as_uuid=True), nullable=False)
    verified = Column(Boolean, nullable=True)                # verify() antes de anclar (None = no se pudo)
    checked = Column(BigInteger, nullable=True)              # filas re-leídas por esa verificación
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=_NOW)
    __table_args__ = (Index('ux_anchor_day_lineage', 'day', 'lineage_id', unique=True),)


class AICall(Base):
    """Paso 21 (§2.6, GV-11): UNA fila por pedido de texto a la IA (cascada de core/ai._ai_complete_raw). La
    escribe SOLO core/ai.py (vía core/ai_calls, en lote y fuera del camino del usuario). Append-only y sellada.
    Nunca texto en claro aquí: el prompt, el system y la salida van como blobs direccionados por hash
    (decision_blobs, retención 'legal' si la llamada ocurrió dentro de una decisión sync; si no, 'standard_90d');
    quién la pidió va como hash. `decision_id` NO tiene FK: las decisiones async (chat, qué-pasaría-si) se
    escriben DESPUÉS de sus llamadas. `model` = el modelo REAL que devolvió el proveedor (no la variable)."""
    __tablename__ = 'ai_calls'
    id = Column(UUID(as_uuid=True), primary_key=True)        # lo reserva core/ai_calls antes de escribir
    seq = Column(BigInteger, Identity(always=True), nullable=False, unique=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    provider = Column(String(20), nullable=True)             # claude|gemini|nvidia (None si nadie respondió)
    model = Column(String(80), nullable=True)
    tier = Column(String(8), nullable=False)
    feature = Column(String(40), nullable=True)
    who_hash = Column(String(16), nullable=True)
    prompt_sha = Column(CHAR(64), nullable=False)
    system_sha = Column(CHAR(64), nullable=False)
    system_blob = Column(CHAR(64), ForeignKey('decision_blobs.sha256'), nullable=True)
    input_blob = Column(CHAR(64), ForeignKey('decision_blobs.sha256'), nullable=True)
    output_sha = Column(CHAR(64), nullable=True)
    output_blob = Column(CHAR(64), ForeignKey('decision_blobs.sha256'), nullable=True)
    tokens_in = Column(Integer, nullable=False, server_default=text('0'))
    tokens_out = Column(Integer, nullable=False, server_default=text('0'))
    cache_read_tokens = Column(Integer, nullable=False, server_default=text('0'))
    cache_write_tokens = Column(Integer, nullable=False, server_default=text('0'))
    cost_usd = Column(Float, nullable=False, server_default=text('0'))
    latency_ms = Column(Integer, nullable=True)
    ok = Column(Boolean, nullable=False)
    error = Column(String(240), nullable=True)
    guardian = Column(JSONB, nullable=True)                  # veredicto del guardián de cifras
    route = Column(JSONB, nullable=True)                     # {order, tried, json, max_tokens}
    decision_id = Column(UUID(as_uuid=True), nullable=True)
    retention_class = Column(String(16), nullable=False)
    txid = Column(XID8(), nullable=False, server_default=txid_default())
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=_NOW)
    __table_args__ = (
        CheckConstraint(_in('retention_class', RETENTION), name='ck_aicall_retention'),
        CheckConstraint(_in('tier', ('fast', 'deep')), name='ck_aicall_tier'),
        Index('ix_aicall_time', text('recorded_at DESC')),
        Index('ix_aicall_decision', 'decision_id'),
        Index('ix_aicall_txid', 'txid'),
    )


LEDGER_TABLES = ('decisions', 'decision_refs', 'decision_outcomes', 'decision_violations', 'ledger_seals',
                 'ledger_meta', 'ledger_anchors', 'ai_calls')
