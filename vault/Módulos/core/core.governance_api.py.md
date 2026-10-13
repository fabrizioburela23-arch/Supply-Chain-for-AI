---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/governance_api.py"
lenguaje: "python"
lineas: 381
aliases: ["core/governance_api.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/governance_api.py

> Módulo · capa [[Capa Infraestructura]] · 381 líneas · `core/governance_api.py`

## Para qué sirve

/api/governance/\* (docs/INFRA_OPERATIVA.md §5.1; paso 9). Nunca bajo /v1/\*.

## API pública

- `gov_active()` _(línea 43)_
- `gov_status()` _(línea 67)_
- `gov_ratify()` _(línea 89)_
- `gov_preview()` _(línea 123)_
- `gov_activate()` _(línea 147)_
- `gov_propose()` _(línea 234)_
- `gov_validate()` _(línea 269)_
- `gov_validation()` _(línea 295)_
- `gov_cancel()` _(línea 313)_
- `gov_history()` _(línea 341)_
- `gov_attribution()` _(línea 366)_

**Internas** (empiezan con `_`): `_need_db`, `_body`, `_gov_error`

## Depende de

- [[core.governance.py]] — importa `governance`
- [[core.governance_flow.py]] — importa `governance_flow`
- [[core.governance_preview.py]] — importa `governance_preview`
- [[core.http.py]] — importa `rate_limit`
- [[core.identity.py]] — importa `identity`
- [[core.pin.py]] — importa `pin`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`

## Lo usan

- [[server.py]] — lo importa

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `POST` | `/api/governance/activate` | `gov_activate` | [[engine.governance.js]], 3 pruebas |
| `GET` | `/api/governance/active` | `gov_active` | 1 prueba |
| `GET` | `/api/governance/attribution` | `gov_attribution` | 1 prueba |
| `POST` | `/api/governance/cancel` | `gov_cancel` | [[engine.governance.js]], 2 pruebas |
| `GET` | `/api/governance/history` | `gov_history` | [[engine.governance.js]], 1 prueba |
| `GET` | `/api/governance/preview` | `gov_preview` | [[engine.governance.js]], 2 pruebas |
| `POST` | `/api/governance/propose` | `gov_propose` | [[engine.governance.js]], 1 prueba |
| `POST` | `/api/governance/ratify` | `gov_ratify` | [[engine.governance.js]], 1 prueba |
| `GET` | `/api/governance/status` | `gov_status` | [[engine.governance.js]], 1 prueba |
| `POST` | `/api/governance/validate` | `gov_validate` | [[engine.governance.js]] |
| `GET` | `/api/governance/validation` | `gov_validation` | [[engine.governance.js]], 1 prueba |

Grupos: [[API governance]]

## Pruebas que lo cubren

- [[tests.test_governance.py]]
- [[tests.test_governance_activation.py]]
- [[tests.test_governance_flow.py]]
- [[tests.test_review_batch_g.py]]
