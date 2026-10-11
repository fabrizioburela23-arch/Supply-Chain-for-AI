---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 1
tags: ["capa/datos-vivo", "tipo/api"]
---

# API fundamentals

> 1 rutas · definidas en [[server.py]] · prefijo `/api/fundamentals`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/fundamentals/<ticker>` | `fundamentals` | [[server.py]] | [[app.html]], [[engine.khipu_lang.js]], [[engine.termdata.js]], 1 prueba |
