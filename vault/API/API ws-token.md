---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 1
tags: ["capa/datos-vivo", "tipo/api"]
---

# API ws-token

> 1 rutas · definidas en [[server.py]] · prefijo `/api/ws-token`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/ws-token` | `ws_token` | [[server.py]] | [[engine.app_main.js]], 1 prueba |
