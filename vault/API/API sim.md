---
tipo: "api"
capa: "Cuantitativo (matrices, tensores, riesgo)"
rutas: 1
tags: ["capa/cuantitativo", "tipo/api"]
---

# API sim

> 1 rutas · definidas en [[server.py]] · prefijo `/api/sim`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `POST` | `/api/sim/agents` | `sim_agents_route` | [[server.py]] | [[core.ai_usage.py]], [[core.decision_sites.py]], [[engine.app_coordinator.js]], [[engine.cockpit.js]], 2 pruebas |
