---
tipo: "api"
capa: "MCP y API"
rutas: 13
tags: ["capa/mcp-api", "tipo/api"]
---

# API MCP transporte y OAuth

> 13 rutas · definidas en [[mcp_server.api.py]], [[mcp_server.oauth.py]] · prefijo `/.well-known/oauth-authorization-server`, `/.well-known/oauth-protected-resource`, `/mcp`, `/oauth/authorize`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET,OPTIONS` | `/.well-known/oauth-authorization-server` | `_meta_as` | [[mcp_server.oauth.py]] | [[mcp_server.api.py]], 1 prueba |
| `GET,OPTIONS` | `/.well-known/oauth-authorization-server/mcp` | `_meta_as` | [[mcp_server.oauth.py]] | — |
| `GET,OPTIONS` | `/.well-known/oauth-protected-resource` | `_meta_resource` | [[mcp_server.oauth.py]] | 1 prueba |
| `GET,OPTIONS` | `/.well-known/oauth-protected-resource/mcp` | `_meta_resource` | [[mcp_server.oauth.py]] | [[mcp_server.api.py]], 1 prueba |
| `DELETE` | `/mcp` | `mcp_delete` | [[mcp_server.api.py]] | [[core.ai_usage.py]], [[engine.mcpconnect.js]], [[mcp_server.api.py]], [[mcp_server.oauth.py]], [[scripts.smoke_mcp.py]], [[server.py]], 2 pruebas |
| `GET` | `/mcp` | `mcp_get` | [[mcp_server.api.py]] | [[core.ai_usage.py]], [[engine.mcpconnect.js]], [[mcp_server.api.py]], [[mcp_server.oauth.py]], [[scripts.smoke_mcp.py]], [[server.py]], 2 pruebas |
| `OPTIONS` | `/mcp` | `mcp_options` | [[mcp_server.api.py]] | [[core.ai_usage.py]], [[engine.mcpconnect.js]], [[mcp_server.api.py]], [[mcp_server.oauth.py]], [[scripts.smoke_mcp.py]], [[server.py]], 2 pruebas |
| `POST` | `/mcp` | `mcp_post` | [[mcp_server.api.py]] | [[core.ai_usage.py]], [[engine.mcpconnect.js]], [[mcp_server.api.py]], [[mcp_server.oauth.py]], [[scripts.smoke_mcp.py]], [[server.py]], 2 pruebas |
| `GET` | `/oauth/authorize` | `oauth_authorize_get` | [[mcp_server.oauth.py]] | [[mcp_server.oauth.py]], 3 pruebas |
| `POST` | `/oauth/authorize` | `oauth_authorize_post` | [[mcp_server.oauth.py]] | [[mcp_server.oauth.py]], 3 pruebas |
| `OPTIONS,POST` | `/oauth/register` | `oauth_register` | [[mcp_server.oauth.py]] | [[mcp_server.oauth.py]], 3 pruebas |
| `OPTIONS,POST` | `/oauth/revoke` | `oauth_revoke` | [[mcp_server.oauth.py]] | [[mcp_server.oauth.py]], 2 pruebas |
| `OPTIONS,POST` | `/oauth/token` | `oauth_token` | [[mcp_server.oauth.py]] | [[mcp_server.oauth.py]], 2 pruebas |
