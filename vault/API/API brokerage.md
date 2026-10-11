---
tipo: "api"
capa: "Dinero (carteras, trading, corretaje)"
rutas: 20
tags: ["capa/dinero", "tipo/api"]
---

# API brokerage

> 20 rutas · definidas en [[brokerage.api.py]] · prefijo `/api/brokerage`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/brokerage/approvals` | `bk_approvals` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/approvals/<preview_id>/approve` | `bk_approve` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/approvals/<preview_id>/reject` | `bk_reject` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
| `GET` | `/api/brokerage/audit` | `bk_audit` | [[brokerage.api.py]] | 1 prueba |
| `GET` | `/api/brokerage/clients` | `bk_clients` | [[brokerage.api.py]] | [[engine.clients.js]], [[engine.mcpconnect.js]], 2 pruebas |
| `POST` | `/api/brokerage/clients` | `bk_client_create` | [[brokerage.api.py]] | [[engine.clients.js]], [[engine.mcpconnect.js]], 2 pruebas |
| `GET` | `/api/brokerage/clients/<client_id>` | `bk_client_get` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
| `PATCH` | `/api/brokerage/clients/<client_id>` | `bk_client_patch` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
| `GET` | `/api/brokerage/clients/<client_id>/account` | `bk_account` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
| `GET` | `/api/brokerage/clients/<client_id>/audit` | `bk_client_audit` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/clients/<client_id>/credentials` | `bk_client_creds` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/clients/<client_id>/oauth/start` | `bk_oauth_start` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/clients/<client_id>/sync` | `bk_sync` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
| `GET` | `/api/brokerage/oauth/callback` | `bk_oauth_callback` | [[brokerage.api.py]] | 1 prueba |
| `GET` | `/api/brokerage/orders` | `bk_orders` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/orders/<order_id>/cancel` | `bk_cancel` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/orders/<preview_id>/confirm` | `bk_confirm` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/orders/preview` | `bk_preview` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
| `GET` | `/api/brokerage/status` | `bk_status` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
| `GET` | `/api/brokerage/status/detail` | `bk_status_detail` | [[brokerage.api.py]] | [[engine.clients.js]], 1 prueba |
