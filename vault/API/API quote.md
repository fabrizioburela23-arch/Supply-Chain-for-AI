---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 1
tags: ["capa/datos-vivo", "tipo/api"]
---

# API quote

> 1 rutas · definidas en [[server.py]] · prefijo `/api/quote`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/quote/<ticker>` | `quote` | [[server.py]] | [[engine.app_main.js]], 2 pruebas |
