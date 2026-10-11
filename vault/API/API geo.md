---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 1
tags: ["capa/datos-vivo", "tipo/api"]
---

# API geo

> 1 rutas · definidas en [[core.geosit.py]] · prefijo `/api/geo`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/geo/situation` | `geo_situation` | [[core.geosit.py]] | [[core.world.py]] |
