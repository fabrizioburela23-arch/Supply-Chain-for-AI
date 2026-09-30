"""mcp_server/models.py — tablas del servidor MCP.

Viven en el MISMO Base que la ontología (ontology/db.init_schema las crea al
importar este módulo). La ontología nunca las toca.

  mcp_tokens         una fila por conexión (token manual o emitido por OAuth).
                     El token NUNCA se guarda: solo su sha256 (token_hash) y
                     un prefijo para reconocerlo en la UI.
  mcp_audit          APPEND-ONLY: cada llamada (método, herramienta, resumen de
                     argumentos SIN secretos, resultado, latencia).
  mcp_oauth_clients  clientes OAuth registrados dinámicamente (RFC 7591).
  mcp_oauth_codes    códigos de autorización de un solo uso (PKCE S256); cada
                     consentimiento firmado se canjea UNA vez (consent_nonce).
"""
import uuid

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from ontology.models import Base

SCOPES = ('read', 'research', 'trade')


def _uuid():
    return uuid.uuid4().hex


class McpToken(Base):
    __tablename__ = 'mcp_tokens'

    id = Column(String(40), primary_key=True, default=_uuid)
    name = Column(String(120), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)   # sha256 hex
    token_prefix = Column(String(16), nullable=False)                           # 'kmcp_AbCd' (para la UI)
    scopes = Column(JSONB, nullable=False, default=list)                        # ⊆ SCOPES
    client_id = Column(String(60), nullable=True)                               # cliente de corretaje (trade)
    created_by = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    use_count = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)                 # NULL = no caduca (manual)
    revoked = Column(Boolean, nullable=False, default=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by = Column(String(120), nullable=True)
    kind = Column(String(10), nullable=False, default='manual')                 # manual | oauth
    oauth_client_id = Column(String(80), nullable=True)
    refresh_hash = Column(String(64), nullable=True, index=True)                # sha256 del refresh token
    oauth_code_hash = Column(String(64), nullable=True, index=True)             # código OAuth que lo emitió


class McpAudit(Base):
    __tablename__ = 'mcp_audit'

    id = Column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    token_id = Column(String(40), nullable=True, index=True)
    token_name = Column(String(120), nullable=True)
    method = Column(String(60), nullable=True)
    tool = Column(String(60), nullable=True, index=True)
    args_summary = Column(JSONB, nullable=False, default=dict)                 # SIN secretos, truncado
    status = Column(String(20), nullable=False)                                  # ok|error|denied|unauthorized|rate_limited
    error = Column(String(300), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    ip = Column(String(64), nullable=True)
    session_id = Column(String(64), nullable=True)
    client_id = Column(String(60), nullable=True)


class McpOAuthClient(Base):
    __tablename__ = 'mcp_oauth_clients'

    client_id = Column(String(80), primary_key=True)
    client_name = Column(String(200), nullable=True)
    redirect_uris = Column(JSONB, nullable=False, default=list)
    token_endpoint_auth_method = Column(String(40), nullable=False, default='none')
    secret_hash = Column(String(64), nullable=True)
    scope = Column(String(200), nullable=True)
    meta = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class McpOAuthCode(Base):
    __tablename__ = 'mcp_oauth_codes'

    code_hash = Column(String(64), primary_key=True)
    oauth_client_id = Column(String(80), nullable=False, index=True)
    redirect_uri = Column(Text, nullable=False)
    code_challenge = Column(String(200), nullable=False)
    scopes = Column(JSONB, nullable=False, default=list)
    broker_client_id = Column(String(60), nullable=True)
    resource = Column(Text, nullable=True)
    token_name = Column(String(120), nullable=True)
    approved_by = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    consent_nonce = Column(String(40), nullable=True, unique=True)              # anti-replay del consentimiento


# Columnas añadidas después de la primera versión: create_all no las añade a
# una tabla existente → auth.with_schema las aplica con ADD COLUMN IF NOT EXISTS.
LATE_COLUMNS = (
    ('mcp_tokens', 'oauth_code_hash', 'VARCHAR(64)'),
    ('mcp_oauth_codes', 'consent_nonce', 'VARCHAR(40)'),
)
