---
tipo: "api"
capa: "Infraestructura"
rutas: 2
tags: ["capa/infraestructura", "tipo/api"]
---

# API ops

> 2 rutas · definidas en [[core.ops_check.py]] · prefijo `/api/ops`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `POST` | `/api/ops/check` | `api_run_check` | [[core.ops_check.py]] | 1 prueba |
| `GET` | `/api/ops/last_check` | `api_last_check` | [[core.ops_check.py]] | 1 prueba |
