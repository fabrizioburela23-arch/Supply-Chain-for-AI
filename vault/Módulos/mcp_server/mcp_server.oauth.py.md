---
tipo: "modulo"
capa: "MCP y API"
ruta: "mcp_server/oauth.py"
lenguaje: "python"
lineas: 781
aliases: ["mcp_server/oauth.py"]
tags: ["capa/mcp-api", "tipo/modulo"]
---

# mcp_server/oauth.py

> Módulo · capa [[Capa MCP y API]] · 781 líneas · `mcp_server/oauth.py`

## Para qué sirve

OAuth 2.1 mínimo (y correcto) para conectores remotos.

## API pública

- `oauth_enabled()` _(línea 61)_
- `sign(obj)` _(línea 115)_
- `unsign(tok)` _(línea 121)_
- `pkce_s256(verifier)` _(línea 135)_
- `valid_redirect_uri(uri)` _(línea 139)_
- `protected_resource_metadata()` _(línea 178)_
- `authorization_server_metadata()` _(línea 187)_
- `register(bp)` _(línea 477)_

**Internas** (empiezan con `_`): `_ttl_hours`, `_now`, `_base`, `_sign_key`, `_insecure_secret`, `_b64u`, `_b64u_dec`, `_json_err`, `_cors_public`, `_session`, `_get_client`, `_client_auth`, `_issue`, `_revoke_from_code`, `_ledger`, `_token_doc`, `_client_principal`, `_ledger_503_json`, `_page`, `_error_page`, `_request_error_page`, `_hidden`, `_redirect_page`, `_validate_auth_request`, `_broker_clients`, `_pin_step`, `_consent_step`

## Depende de

- [[brokerage.service.py]] — importa `(dinámico: brokerage.service)`
- [[core.decision_sites.py]] — importa `decision_sites`
- [[core.decisions.py]] — importa `LedgerUnavailable`
- [[core.http.py]] — importa `rate_limit`
- [[core.identity.py]] — importa `identity`
- [[core.pin.py]] — importa `insecure_production_secret`
- [[mcp_server.api.py]] — importa `base_url`
- [[mcp_server.auth.py]] — importa `auth`
- [[mcp_server.models.py]] — importa `McpOAuthClient`, `McpOAuthCode`, `McpToken`
- [[ontology.db.py]] — importa `session_scope`

## Lo usan

- [[mcp_server.api.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET,OPTIONS` | `/.well-known/oauth-authorization-server` | `_meta_as` | [[mcp_server.api.py]], 1 prueba |
| `GET,OPTIONS` | `/.well-known/oauth-authorization-server/mcp` | `_meta_as` | — |
| `GET,OPTIONS` | `/.well-known/oauth-protected-resource` | `_meta_resource` | 1 prueba |
| `GET,OPTIONS` | `/.well-known/oauth-protected-resource/mcp` | `_meta_resource` | [[mcp_server.api.py]], 1 prueba |
| `GET` | `/oauth/authorize` | `oauth_authorize_get` | 3 pruebas |
| `POST` | `/oauth/authorize` | `oauth_authorize_post` | 3 pruebas |
| `OPTIONS,POST` | `/oauth/register` | `oauth_register` | 3 pruebas |
| `OPTIONS,POST` | `/oauth/revoke` | `oauth_revoke` | 2 pruebas |
| `OPTIONS,POST` | `/oauth/token` | `oauth_token` | 2 pruebas |

Grupos: [[API MCP transporte y OAuth]]

## Endpoints que llama

- `DELETE /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `GET /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `GET /oauth/authorize` → [[mcp_server.oauth.py]] ([[API MCP transporte y OAuth]])
- `OPTIONS /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `OPTIONS,POST /oauth/register` → [[mcp_server.oauth.py]] ([[API MCP transporte y OAuth]])
- `OPTIONS,POST /oauth/revoke` → [[mcp_server.oauth.py]] ([[API MCP transporte y OAuth]])
- `OPTIONS,POST /oauth/token` → [[mcp_server.oauth.py]] ([[API MCP transporte y OAuth]])
- `POST /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `POST /oauth/authorize` → [[mcp_server.oauth.py]] ([[API MCP transporte y OAuth]])

## Variables de entorno que lee (solo nombres)

- [[ENV MCP_OAUTH_ENABLED]]
- [[ENV MCP_OAUTH_TTL_HOURS]]
- [[ENV SECRET_KEY]]

## Pruebas que lo cubren

- [[tests.test_mcp.py]]
- [[tests.test_rutas_acceso_decision.py]]
- [[tests.test_security.py]]
