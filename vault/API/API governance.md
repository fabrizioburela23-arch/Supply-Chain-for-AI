---
tipo: "api"
capa: "Infraestructura"
rutas: 3
tags: ["capa/infraestructura", "tipo/api"]
---

# API governance

> 3 rutas · definidas en [[core.governance_api.py]] · prefijo `/api/governance`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/governance/active` | `gov_active` | [[core.governance_api.py]] | 1 prueba |
| `POST` | `/api/governance/ratify` | `gov_ratify` | [[core.governance_api.py]] | 1 prueba |
| `GET` | `/api/governance/status` | `gov_status` | [[core.governance_api.py]] | 1 prueba |
