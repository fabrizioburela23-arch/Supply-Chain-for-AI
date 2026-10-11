---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 1
tags: ["capa/datos-vivo", "tipo/api"]
---

# API investors

> 1 rutas · definidas en [[server.py]] · prefijo `/api/investors`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/investors/13f/<ticker>` | `investors_13f` | [[server.py]] | [[app.html]] |
