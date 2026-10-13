---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 2
tags: ["capa/datos-vivo", "tipo/api"]
---

# API space

> 2 rutas · definidas en [[server.py]] · prefijo `/api/space`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/space/launches` | `space_launches` | [[server.py]] | [[engine.voice.js]], 1 prueba |
| `GET` | `/api/space/tle` | `space_tle` | [[server.py]] | [[engine.spacemonitor.js]], [[engine.voice.js]], 1 prueba |
