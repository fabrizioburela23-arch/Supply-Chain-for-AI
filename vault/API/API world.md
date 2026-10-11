---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 6
tags: ["capa/datos-vivo", "tipo/api"]
---

# API world

> 6 rutas · definidas en [[core.world.py]] · prefijo `/api/world`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/world/brief` | `api_world_brief` | [[core.world.py]] | [[engine.worldmonitor.js]], [[sim.scenario_builder.js]], 1 prueba |
| `GET` | `/api/world/events` | `api_world_events` | [[core.world.py]] | [[engine.worldmonitor.js]], 1 prueba |
| `GET` | `/api/world/exposure` | `api_world_exposure` | [[core.world.py]] | [[engine.worldmonitor.js]], 1 prueba |
| `GET` | `/api/world/gpr` | `api_world_gpr` | [[core.world.py]] | [[engine.worldmonitor.js]], [[sim.scenario_builder.js]] |
| `GET` | `/api/world/policy` | `api_world_policy` | [[core.world.py]] | [[engine.worldmonitor.js]], [[sim.scenario_builder.js]] |
| `GET` | `/api/world/reference` | `api_world_reference` | [[core.world.py]] | [[engine.worldmonitor.js]], 1 prueba |
