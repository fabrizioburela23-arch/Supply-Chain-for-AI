---
tipo: "modulo"
capa: "MCP y API"
ruta: "mcp_server/api.py"
lenguaje: "python"
lineas: 702
aliases: ["mcp_server/api.py"]
tags: ["capa/mcp-api", "tipo/modulo"]
---

# mcp_server/api.py

> Módulo · capa [[Capa MCP y API]] · 702 líneas · `mcp_server/api.py`

## Para qué sirve

blueprint mcp_bp (transporte + administración).

## API pública

- `mcp_enabled()` _(línea 72)_
- `base_url()` — URL pública (para metadatos OAuth y configuraciones). MCP_PUBLIC_URL manda; si no, el Host de la petición + X-Forwarded-Proto (Railway … _(línea 76)_
- `resource_url()` _(línea 88)_
- `resource_metadata_url()` _(línea 92)_
- `known_origins()` — Orígenes de confianza FIJOS (no dependen de la petición). _(línea 126)_
- `origin_allowed(origin)` — Protección DNS-rebinding (spec «Security Warning»). Sin Origin (clientes de servidor/CLI) → se permite. Con Origin, debe estar en la lista … _(línea 140)_
- `host_allowed()` — MCP_ALLOWED_HOSTS (opcional, 'a.example,b.example:8080'): si está, el Host debe coincidir. _(línea 158)_
- `mcp_options()` _(línea 262)_
- `mcp_get()` _(línea 270)_
- `mcp_delete()` _(línea 278)_
- `mcp_post()` _(línea 300)_
- `ledger_tool_call(audit, resp, session_id=…, latency_ms=…)` — Ficha `mcp.tool_call` (paso 20, §2.5; cierra MAP 2 #15): quién (mcp:&lt;token_id>, del token), qué herramienta, la HUELLA de los argumentos … _(línea 433)_
- `mcp_status()` _(línea 533)_
- `mcp_tools_catalog()` _(línea 561)_
- `mcp_tokens_list()` _(línea 567)_
- `mcp_tokens_create()` _(línea 613)_
- `mcp_tokens_revoke(token_id)` _(línea 648)_
- `mcp_audit_list()` _(línea 677)_

**Internas** (empiezan con `_`): `_ip`, `_origin_of`, `_allowed_origins`, `_request_hostname`, `_guard_origin_host`, `_cors`, `_rpc_http`, `_unauthorized`, `_backend_down`, `_authenticate`, `_new_session`, `_close_session`, `_session_state`, `_reject_constant`, `_mcp_post_body`, `_pin_guard`, `_actor`, `_brokerage_available`, `_secret_key_insecure`, `_ledger_token`, `_ledger_503`

## Depende de

- [[brokerage.service.py]] — importa `(dinámico: brokerage.service)`
- [[core.decision_sites.py]] — importa `decision_sites`
- [[core.decisions.py]] — importa `LedgerUnavailable`, `decisions`
- [[core.http.py]] — importa `rate_limit`
- [[core.identity.py]] — importa `identity`
- [[core.pin.py]] — importa `insecure_production_secret`
- [[mcp_server.auth.py]] — importa `auth`
- [[mcp_server.models.py]] — importa `McpToken`
- [[mcp_server.oauth.py]] — importa `oauth`
- [[mcp_server.protocol.py]] — importa `protocol`
- [[mcp_server.tools.py]] — importa `tools`
- [[ontology.db.py]] — importa `session_scope`

## Lo usan

- [[mcp_server.oauth.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 6 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/mcp/audit` | `mcp_audit_list` | [[engine.mcpconnect.js]], 2 pruebas |
| `GET` | `/api/mcp/status` | `mcp_status` | [[engine.mcpconnect.js]], 2 pruebas |
| `GET` | `/api/mcp/tokens` | `mcp_tokens_list` | [[engine.mcpconnect.js]], 5 pruebas |
| `POST` | `/api/mcp/tokens` | `mcp_tokens_create` | [[engine.mcpconnect.js]], 5 pruebas |
| `POST` | `/api/mcp/tokens/<token_id>/revoke` | `mcp_tokens_revoke` | [[engine.mcpconnect.js]], 4 pruebas |
| `GET` | `/api/mcp/tools` | `mcp_tools_catalog` | [[engine.mcpconnect.js]], 1 prueba |
| `DELETE` | `/mcp` | `mcp_delete` | [[core.ai_usage.py]], [[engine.mcpconnect.js]], [[mcp_server.oauth.py]], [[scripts.smoke_mcp.py]], [[server.py]], 2 pruebas |
| `GET` | `/mcp` | `mcp_get` | [[core.ai_usage.py]], [[engine.mcpconnect.js]], [[mcp_server.oauth.py]], [[scripts.smoke_mcp.py]], [[server.py]], 2 pruebas |
| `OPTIONS` | `/mcp` | `mcp_options` | [[core.ai_usage.py]], [[engine.mcpconnect.js]], [[mcp_server.oauth.py]], [[scripts.smoke_mcp.py]], [[server.py]], 2 pruebas |
| `POST` | `/mcp` | `mcp_post` | [[core.ai_usage.py]], [[engine.mcpconnect.js]], [[mcp_server.oauth.py]], [[scripts.smoke_mcp.py]], [[server.py]], 2 pruebas |

Grupos: [[API MCP transporte y OAuth]], [[API mcp]]

## Endpoints que llama

- `DELETE /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `GET /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `GET,OPTIONS /.well-known/oauth-authorization-server` → [[mcp_server.oauth.py]] ([[API MCP transporte y OAuth]])
- `GET,OPTIONS /.well-known/oauth-protected-resource/mcp` → [[mcp_server.oauth.py]] ([[API MCP transporte y OAuth]])
- `OPTIONS /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `POST /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])

## Variables de entorno que lee (solo nombres)

- [[ENV MCP_ALLOWED_HOSTS]]
- [[ENV MCP_ALLOWED_ORIGINS]]
- [[ENV MCP_ENABLED]]
- [[ENV MCP_PUBLIC_URL]]
- [[ENV MCP_STATIC_TOKEN]]
- [[ENV RAILWAY_PUBLIC_DOMAIN]]
- [[ENV TRADE_PIN]]

## Pruebas que lo cubren

- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_mcp.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_repair_ops.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_rutas_acceso_decision.py]]
- [[tests.test_security.py]]
