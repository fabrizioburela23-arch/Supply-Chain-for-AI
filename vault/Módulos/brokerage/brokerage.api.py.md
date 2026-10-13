---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "brokerage/api.py"
lenguaje: "python"
lineas: 419
aliases: ["brokerage/api.py"]
tags: ["capa/dinero", "tipo/modulo"]
---

# brokerage/api.py

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 419 líneas · `brokerage/api.py`

## Para qué sirve

blueprint /api/brokerage/\* (corretaje multi-cliente).

## API pública

- `guarded(f)` — PIN + base de datos + manejo uniforme de errores. _(línea 105)_
- `bk_status()` — SIN PIN: solo si está disponible y si el interruptor está encendido (la postura de seguridad —cifrado, auto-aprobación…— va en … _(línea 178)_
- `bk_status_detail()` _(línea 191)_
- `bk_clients()` _(línea 207)_
- `bk_client_create()` _(línea 215)_
- `bk_client_get(client_id)` _(línea 226)_
- `bk_client_patch(client_id)` _(línea 238)_
- `bk_client_creds(client_id)` _(línea 249)_
- `bk_oauth_start(client_id)` _(línea 260)_
- `bk_account(client_id)` _(línea 269)_
- `bk_sync(client_id)` _(línea 279)_
- `bk_client_audit(client_id)` _(línea 288)_
- `bk_audit()` _(línea 297)_
- `bk_preview()` _(línea 306)_
- `bk_confirm(preview_id)` _(línea 318)_
- `bk_orders()` _(línea 331)_
- `bk_cancel(order_id)` _(línea 341)_
- `bk_approvals()` _(línea 351)_
- `bk_approve(preview_id)` _(línea 359)_
- `bk_reject(preview_id)` _(línea 368)_
- `bk_oauth_callback()` _(línea 388)_

**Internas** (empiezan con `_`): `_db_ok`, `_unavailable`, `_audit_global_lock`, `_pin_error`, `_with_schema`, `_body`, `_principal`, `_actor`, `_svc`, `_session`, `_res`

## Depende de

- [[brokerage.service.py]] — importa `audit`, `service`
- [[core.http.py]] — importa `rate_limit`
- [[core.identity.py]] — importa `identity`
- [[core.pin.py]] — importa `pin`
- [[ontology.db.py]] — importa `init_schema`, `ontology_available`, `session_scope`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 3 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/brokerage/approvals` | `bk_approvals` | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/approvals/<preview_id>/approve` | `bk_approve` | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/approvals/<preview_id>/reject` | `bk_reject` | [[engine.clients.js]], 1 prueba |
| `GET` | `/api/brokerage/audit` | `bk_audit` | 1 prueba |
| `GET` | `/api/brokerage/clients` | `bk_clients` | [[engine.clients.js]], [[engine.mcpconnect.js]], 2 pruebas |
| `POST` | `/api/brokerage/clients` | `bk_client_create` | [[engine.clients.js]], [[engine.mcpconnect.js]], 2 pruebas |
| `GET` | `/api/brokerage/clients/<client_id>` | `bk_client_get` | [[engine.clients.js]], 1 prueba |
| `PATCH` | `/api/brokerage/clients/<client_id>` | `bk_client_patch` | [[engine.clients.js]], 1 prueba |
| `GET` | `/api/brokerage/clients/<client_id>/account` | `bk_account` | [[engine.clients.js]], 1 prueba |
| `GET` | `/api/brokerage/clients/<client_id>/audit` | `bk_client_audit` | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/clients/<client_id>/credentials` | `bk_client_creds` | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/clients/<client_id>/oauth/start` | `bk_oauth_start` | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/clients/<client_id>/sync` | `bk_sync` | [[engine.clients.js]], 1 prueba |
| `GET` | `/api/brokerage/oauth/callback` | `bk_oauth_callback` | 1 prueba |
| `GET` | `/api/brokerage/orders` | `bk_orders` | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/orders/<order_id>/cancel` | `bk_cancel` | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/orders/<preview_id>/confirm` | `bk_confirm` | [[engine.clients.js]], 1 prueba |
| `POST` | `/api/brokerage/orders/preview` | `bk_preview` | [[engine.clients.js]], 1 prueba |
| `GET` | `/api/brokerage/status` | `bk_status` | [[engine.clients.js]], 1 prueba |
| `GET` | `/api/brokerage/status/detail` | `bk_status_detail` | [[engine.clients.js]], 1 prueba |

Grupos: [[API brokerage]]

## Pruebas que lo cubren

- [[tests.test_brokerage.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_security.py]]
