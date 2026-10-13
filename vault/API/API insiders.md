---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 1
tags: ["capa/datos-vivo", "tipo/api"]
---

# API insiders

> 1 rutas · definidas en [[server.py]] · prefijo `/api/insiders`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/insiders/<ticker>` | `insiders` | [[server.py]] | [[engine.app_main.js]] |
