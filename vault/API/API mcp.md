---
tipo: "api"
capa: "MCP y API"
rutas: 6
tags: ["capa/mcp-api", "tipo/api"]
---

# API mcp

> 6 rutas · definidas en [[mcp_server.api.py]] · prefijo `/api/mcp`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/mcp/audit` | `mcp_audit_list` | [[mcp_server.api.py]] | [[engine.mcpconnect.js]], 2 pruebas |
| `GET` | `/api/mcp/status` | `mcp_status` | [[mcp_server.api.py]] | [[engine.mcpconnect.js]], 2 pruebas |
| `GET` | `/api/mcp/tokens` | `mcp_tokens_list` | [[mcp_server.api.py]] | [[engine.mcpconnect.js]], 4 pruebas |
| `POST` | `/api/mcp/tokens` | `mcp_tokens_create` | [[mcp_server.api.py]] | [[engine.mcpconnect.js]], 4 pruebas |
| `POST` | `/api/mcp/tokens/<token_id>/revoke` | `mcp_tokens_revoke` | [[mcp_server.api.py]] | [[engine.mcpconnect.js]], 3 pruebas |
| `GET` | `/api/mcp/tools` | `mcp_tools_catalog` | [[mcp_server.api.py]] | [[engine.mcpconnect.js]], 1 prueba |
