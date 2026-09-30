"""brokerage/models.py — tablas del corretaje multi-cliente.

Viven en el MISMO Base que la ontología (ontology/db.init_schema las crea al
importar este módulo). Son tablas propias: la ontología nunca las toca.

  broker_clients       — una fila por persona/cuenta. Las credenciales van
                         CIFRADAS (enc_credentials, ver brokerage/crypto.py) y
                         jamás salen en una respuesta.
  broker_orders        — previsualizaciones Y órdenes (mismo registro que
                         avanza de estado: previewed → pending_approval →
                         approved → submitted → filled…). Su `id` es también
                         el client_order_id que se envía a Alpaca
                         (idempotencia: la misma previsualización nunca crea
                         dos órdenes).
  broker_audit         — APPEND-ONLY: cada acción (crear cliente, conectar,
                         previsualizar, aprobar, enviar, cancelar…) con quién y
                         cuándo. Nunca se actualiza ni se borra — lo IMPONE un
                         trigger de Postgres (UPDATE/DELETE/TRUNCATE → error),
                         creado por `_after_create` al correr init_schema.
  broker_oauth_states  — `state` de un solo uso del flujo OAuth de Alpaca.
"""
import uuid

import logging

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Float, Index, String, Text, event, func, text)
from sqlalchemy.dialects.postgresql import JSONB

from ontology.models import Base

MODES = ('paper', 'live')
AUTH_TYPES = ('env', 'keys', 'oauth')
RISK_PROFILES = ('conservador', 'moderado', 'agresivo')
CLIENT_STATUSES = ('active', 'paused')
ORDER_STATUSES = ('previewed', 'pending_approval', 'approved', 'submitted', 'filled',
                  'partially_filled', 'canceled', 'rejected', 'expired', 'failed')
SOURCES = ('ui', 'mcp', 'committee')

log = logging.getLogger('khipu')


def _uuid():
    return str(uuid.uuid4())


class BrokerClient(Base):
    __tablename__ = 'broker_clients'

    id = Column(String(40), primary_key=True, default=_uuid)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    mode = Column(String(8), nullable=False, default='paper')            # paper | live
    live_enabled = Column(Boolean, nullable=False, default=False)          # 2º candado del dinero real
    auth_type = Column(String(8), nullable=False, default='keys')          # env | keys | oauth
    enc_credentials = Column(Text, nullable=True)                          # Fernet — NUNCA se devuelve
    credentials_hint = Column(String(40), nullable=True)                   # '****1234' (enmascarado)
    base_url = Column(String(200), nullable=True)                          # solo hosts de Alpaca
    risk_profile = Column(String(16), nullable=False, default='moderado')
    risk_limits = Column(JSONB, nullable=False, default=dict)              # overrides numéricos
    mandate = Column(JSONB, nullable=False, default=dict)                  # clases de activo, símbolos
    status = Column(String(10), nullable=False, default='active')          # active | paused
    hwm_equity = Column(Float, nullable=True)                              # máximo histórico observado
    hwm_at = Column(DateTime(timezone=True), nullable=True)
    last_equity = Column(Float, nullable=True)                             # último dato leído de Alpaca
    last_snapshot_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class BrokerOrder(Base):
    __tablename__ = 'broker_orders'

    id = Column(String(40), primary_key=True, default=_uuid)   # = client_order_id en Alpaca
    client_id = Column(String(40), nullable=False, index=True)
    symbol = Column(String(20), nullable=False)
    side = Column(String(4), nullable=False)                   # buy | sell
    notional = Column(Float, nullable=True)                    # USD
    qty = Column(Float, nullable=True)
    order_type = Column(String(10), nullable=False, default='market')
    limit_price = Column(Float, nullable=True)
    time_in_force = Column(String(6), nullable=True)
    est_price = Column(Float, nullable=True)                   # precio de referencia al previsualizar
    est_usd = Column(Float, nullable=True)                     # monto estimado en USD
    mode = Column(String(8), nullable=True)                    # modo del cliente al previsualizar
    status = Column(String(20), nullable=False, default='previewed', index=True)
    alpaca_status = Column(String(30), nullable=True)          # estado crudo de Alpaca
    source = Column(String(12), nullable=False, default='ui')  # ui | mcp | committee
    requires_approval = Column(Boolean, nullable=False, default=False)
    proposal_id = Column(String(60), nullable=True, index=True)
    rationale = Column(Text, nullable=True)
    checks = Column(JSONB, nullable=False, default=list)
    summary_es = Column(Text, nullable=True)
    summary_en = Column(Text, nullable=True)
    requested_by = Column(String(120), nullable=True)
    approved_by = Column(String(120), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    alpaca_order_id = Column(String(64), nullable=True, index=True)
    client_order_id = Column(String(64), nullable=True, index=True)
    filled_qty = Column(Float, nullable=True)
    filled_avg_price = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    error_en = Column(Text, nullable=True)                     # el mismo error en inglés (UI bilingüe)
    # huella de la cuenta (modo + URL + credenciales) al previsualizar: si cambia
    # antes de ejecutar (p. ej. papel → dinero real), la orden NO se envía
    account_fp = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('ix_broker_orders_client_created', 'client_id', 'created_at'),
    )


class BrokerAudit(Base):
    """APPEND-ONLY. El código de brokerage/ solo hace INSERT aquí."""
    __tablename__ = 'broker_audit'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    actor = Column(String(120), nullable=False)
    action = Column(String(40), nullable=False, index=True)
    client_id = Column(String(40), nullable=True, index=True)
    order_id = Column(String(40), nullable=True, index=True)
    detail = Column(JSONB, nullable=False, default=dict)


class BrokerOAuthState(Base):
    __tablename__ = 'broker_oauth_states'

    state = Column(String(120), primary_key=True)
    client_id = Column(String(40), nullable=False, index=True)
    env = Column(String(8), nullable=False, default='paper')   # paper | live
    created_by = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    used = Column(Boolean, nullable=False, default=False)


# ── esquema tardío + auditoría inmutable ─────────────────────────────────────
# `create_all` no añade columnas a tablas que ya existen: se añaden aquí con
# ADD COLUMN IF NOT EXISTS (idempotente). El trigger hace que broker_audit sea
# de verdad append-only (cualquier UPDATE/DELETE/TRUNCATE falla), también desde
# una consola o un script. Corre tras CADA Base.metadata.create_all (init_schema)
# y cada paso va en su propio SAVEPOINT: un fallo nunca rompe el arranque.
_LATE_COLUMNS = (
    ('broker_orders', 'error_en', 'TEXT'),
    ('broker_orders', 'account_fp', 'VARCHAR(64)'),
)
_AUDIT_FN = """
CREATE OR REPLACE FUNCTION broker_audit_append_only() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'broker_audit es append-only: % no permitido (append-only audit log)', TG_OP;
END;
$$ LANGUAGE plpgsql
"""
_AUDIT_TRG = """
DO $$
BEGIN
  IF to_regclass('broker_audit') IS NOT NULL THEN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'broker_audit_no_modify'
                   AND tgrelid = 'broker_audit'::regclass) THEN
      CREATE TRIGGER broker_audit_no_modify BEFORE UPDATE OR DELETE ON broker_audit
        FOR EACH ROW EXECUTE PROCEDURE broker_audit_append_only();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'broker_audit_no_truncate'
                   AND tgrelid = 'broker_audit'::regclass) THEN
      CREATE TRIGGER broker_audit_no_truncate BEFORE TRUNCATE ON broker_audit
        FOR EACH STATEMENT EXECUTE PROCEDURE broker_audit_append_only();
    END IF;
  END IF;
END $$
"""


def _safe_ddl(connection, sql):
    try:
        with connection.begin_nested():
            connection.execute(text(sql))
        return True
    except Exception as e:  # noqa: BLE001
        log.warning('brokerage: DDL de esquema no aplicado (%s)', type(e).__name__)
        return False


@event.listens_for(Base.metadata, 'after_create')
def _after_create(target, connection, **kw):
    if connection.dialect.name != 'postgresql':
        return
    for table, col, typ in _LATE_COLUMNS:
        _safe_ddl(connection, f'ALTER TABLE IF EXISTS {table} ADD COLUMN IF NOT EXISTS {col} {typ}')
    if _safe_ddl(connection, _AUDIT_FN):
        _safe_ddl(connection, _AUDIT_TRG)
