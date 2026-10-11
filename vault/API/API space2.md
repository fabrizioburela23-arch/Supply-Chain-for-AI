---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 2
tags: ["capa/datos-vivo", "tipo/api"]
---

# API space2

> 2 rutas · definidas en [[core.space.py]] · prefijo `/api/space2`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/space2/launches` | `api_space2_launches` | [[core.space.py]] | [[engine.spacemonitor.js]], 1 prueba |
| `GET` | `/api/space2/summary` | `api_space2_summary` | [[core.space.py]] | [[engine.spacemonitor.js]], 1 prueba |
