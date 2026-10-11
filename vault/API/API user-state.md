---
tipo: "api"
capa: "Infraestructura"
rutas: 1
tags: ["capa/infraestructura", "tipo/api"]
---

# API user-state

> 1 rutas · definidas en [[core.portfolio_reports_api.py]] · prefijo `/api/user-state`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET,PUT` | `/api/user-state` | `user_state` | [[core.portfolio_reports_api.py]] | [[engine.sync.js]], 1 prueba |
