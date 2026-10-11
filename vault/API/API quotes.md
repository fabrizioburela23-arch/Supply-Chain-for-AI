---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 2
tags: ["capa/datos-vivo", "tipo/api"]
---

# API quotes

> 2 rutas · definidas en [[server.py]] · prefijo `/api/quotes`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/quotes` | `batch_quotes` | [[server.py]] | [[engine.canvas-data.js]], 2 pruebas |
| `POST` | `/api/quotes/live` | `quotes_live` | [[server.py]] | [[app.html]], [[engine.worldmonitor.js]], 1 prueba |
