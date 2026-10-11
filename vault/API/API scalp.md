---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 1
tags: ["capa/datos-vivo", "tipo/api"]
---

# API scalp

> 1 rutas · definidas en [[server.py]] · prefijo `/api/scalp`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/scalp/price/<path:symbol>` | `scalp_price` | [[server.py]] | [[engine.cockpit.js]], 2 pruebas |
