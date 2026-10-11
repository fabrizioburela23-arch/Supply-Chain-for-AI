---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 1
tags: ["capa/datos-vivo", "tipo/api"]
---

# API marketstack

> 1 rutas · definidas en [[server.py]] · prefijo `/api/marketstack`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/marketstack` | `marketstack_proxy` | [[server.py]] | [[app.html]] |
