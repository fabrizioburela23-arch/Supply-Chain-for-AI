---
tipo: "api"
capa: "MCP y API"
rutas: 5
tags: ["capa/mcp-api", "tipo/api"]
---

# API v1 (pública)

> 5 rutas · definidas en [[server.py]] · prefijo `/docs`, `/v1/auth`, `/v1/nodes`, `/v1/risk`

**API pública MONETIZADA por tiers (JWT). No se usa para funciones internas.**

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/docs` | `api_docs` | [[server.py]] | — |
| `POST` | `/v1/auth/key` | `api_issue_key` | [[server.py]] | [[app.html]], [[security_audit.py]] |
| `GET` | `/v1/nodes` | `api_nodes` | [[server.py]] | — |
| `GET` | `/v1/nodes/<node_id>/live` | `api_node_live` | [[server.py]] | — |
| `POST` | `/v1/risk/portfolio` | `api_portfolio_risk` | [[server.py]] | 1 prueba |
