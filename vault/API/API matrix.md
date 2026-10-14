---
tipo: "api"
capa: "Cuantitativo (matrices, tensores, riesgo)"
rutas: 11
tags: ["capa/cuantitativo", "tipo/api"]
---

# API matrix

> 11 rutas · definidas en [[matrix.api.py]] · prefijo `/api/matrix`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/matrix/<rel_type>` | `matrix_get` | [[matrix.api.py]] | [[engine.cockpit.js]], [[engine.khipu_lang.js]], [[engine.livesim.js]], [[engine.voice.js]], [[engine.worldmonitor.js]], [[matrix.api.py]], 15 pruebas |
| `POST` | `/api/matrix/factor/fire` | `matrix_factor_fire` | [[matrix.api.py]] | [[engine.app_coordinator.js]], [[engine.khipu_lang.js]], [[matrix.api.py]], 4 pruebas |
| `GET` | `/api/matrix/factors` | `matrix_factors` | [[matrix.api.py]] | [[engine.khipu_lang.js]], 5 pruebas |
| `POST` | `/api/matrix/impact` | `matrix_impact` | [[matrix.api.py]] | [[engine.worldmonitor.js]], [[matrix.api.py]], 7 pruebas |
| `POST` | `/api/matrix/insights` | `matrix_insights` | [[matrix.api.py]] | [[engine.cockpit.js]], [[engine.voice.js]], 4 pruebas |
| `GET` | `/api/matrix/insights/history` | `matrix_insights_history` | [[matrix.api.py]] | [[engine.insights.js]], 1 prueba |
| `GET` | `/api/matrix/metrics` | `matrix_metrics` | [[matrix.api.py]] | 7 pruebas |
| `GET` | `/api/matrix/parity` | `matrix_parity` | [[matrix.api.py]] | 2 pruebas |
| `GET` | `/api/matrix/simulations` | `matrix_list_sims` | [[matrix.api.py]] | [[engine.livesim.js]], 4 pruebas |
| `POST` | `/api/matrix/simulations` | `matrix_save_sim` | [[matrix.api.py]] | [[engine.livesim.js]], 4 pruebas |
| `GET` | `/api/matrix/status` | `matrix_status` | [[matrix.api.py]] | [[engine.worldmonitor.js]], 3 pruebas |
