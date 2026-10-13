---
tipo: "api"
capa: "Infraestructura"
rutas: 11
tags: ["capa/infraestructura", "tipo/api"]
---

# API governance

> 11 rutas · definidas en [[core.governance_api.py]] · prefijo `/api/governance`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `POST` | `/api/governance/activate` | `gov_activate` | [[core.governance_api.py]] | [[engine.governance.js]], 3 pruebas |
| `GET` | `/api/governance/active` | `gov_active` | [[core.governance_api.py]] | 1 prueba |
| `GET` | `/api/governance/attribution` | `gov_attribution` | [[core.governance_api.py]] | 1 prueba |
| `POST` | `/api/governance/cancel` | `gov_cancel` | [[core.governance_api.py]] | [[engine.governance.js]], 2 pruebas |
| `GET` | `/api/governance/history` | `gov_history` | [[core.governance_api.py]] | [[engine.governance.js]], 1 prueba |
| `GET` | `/api/governance/preview` | `gov_preview` | [[core.governance_api.py]] | [[engine.governance.js]], 2 pruebas |
| `POST` | `/api/governance/propose` | `gov_propose` | [[core.governance_api.py]] | [[engine.governance.js]], 1 prueba |
| `POST` | `/api/governance/ratify` | `gov_ratify` | [[core.governance_api.py]] | [[engine.governance.js]], 1 prueba |
| `GET` | `/api/governance/status` | `gov_status` | [[core.governance_api.py]] | [[engine.governance.js]], 1 prueba |
| `POST` | `/api/governance/validate` | `gov_validate` | [[core.governance_api.py]] | [[engine.governance.js]] |
| `GET` | `/api/governance/validation` | `gov_validation` | [[core.governance_api.py]] | [[engine.governance.js]], 1 prueba |
