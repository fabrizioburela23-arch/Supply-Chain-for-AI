---
tipo: "api"
capa: "Infraestructura"
rutas: 1
tags: ["capa/infraestructura", "tipo/api"]
---

# API thesis

> 1 rutas · definidas en [[server.py]] · prefijo `/api/thesis`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `POST` | `/api/thesis/quick` | `thesis_quick` | [[server.py]] | [[core.ai_usage.py]], [[engine.cockpit.js]], 2 pruebas |
