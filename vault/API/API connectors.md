---
tipo: "api"
capa: "Infraestructura"
rutas: 5
tags: ["capa/infraestructura", "tipo/api"]
---

# API connectors

> 5 rutas · definidas en [[core.connectors_api.py]] · prefijo `/api/connectors`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `POST` | `/api/connectors/confirm` | `confirm` | [[core.connectors_api.py]] | [[engine.connectors.js]], 1 prueba |
| `POST` | `/api/connectors/discard` | `discard` | [[core.connectors_api.py]] | [[engine.connectors.js]], 1 prueba |
| `POST` | `/api/connectors/link` | `link` | [[core.connectors_api.py]] | [[engine.connectors.js]] |
| `GET` | `/api/connectors/pending` | `pending_list` | [[core.connectors_api.py]] | [[engine.connectors.js]], 1 prueba |
| `GET` | `/api/connectors/status` | `status` | [[core.connectors_api.py]] | [[engine.connectors.js]] |
