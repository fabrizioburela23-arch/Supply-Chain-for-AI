---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 1
tags: ["capa/datos-vivo", "tipo/api"]
---

# API candles

> 1 rutas · definidas en [[server.py]] · prefijo `/api/candles`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/candles/<ticker>` | `candles` | [[server.py]] | [[app.html]], [[engine.fincard.js]], [[engine.localcharts.js]], [[engine.secondbrain.js]] |
