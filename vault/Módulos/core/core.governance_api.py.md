---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/governance_api.py"
lenguaje: "python"
lineas: 171
aliases: ["core/governance_api.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/governance_api.py

> Módulo · capa [[Capa Infraestructura]] · 171 líneas · `core/governance_api.py`

## Para qué sirve

/api/governance/\* (docs/INFRA_OPERATIVA.md §5.1; paso 9). Nunca bajo /v1/\*.

## API pública

- `gov_active()` _(línea 28)_
- `gov_status()` _(línea 52)_
- `gov_ratify()` _(línea 74)_
- `gov_preview()` _(línea 108)_
- `gov_activate()` _(línea 131)_

## Depende de

- [[core.governance.py]] — importa `governance`
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
| `POST` | `/api/governance/activate` | `gov_activate` | [[engine.governance.js]], 1 prueba |
| `GET` | `/api/governance/active` | `gov_active` | 1 prueba |
| `GET` | `/api/governance/preview` | `gov_preview` | [[engine.governance.js]], 1 prueba |
| `POST` | `/api/governance/ratify` | `gov_ratify` | [[engine.governance.js]], 1 prueba |
| `GET` | `/api/governance/status` | `gov_status` | [[engine.governance.js]], 1 prueba |

Grupos: [[API governance]]

## Pruebas que lo cubren

- [[tests.test_governance.py]]
- [[tests.test_governance_activation.py]]
