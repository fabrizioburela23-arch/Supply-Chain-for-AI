---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 1
tags: ["capa/datos-vivo", "tipo/api"]
---

# API ws-key

> 1 rutas · definidas en [[server.py]] · prefijo `/api/ws-key`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `POST` | `/api/ws-key` | `ws_key` | [[server.py]] | [[app.html]], [[server.py]], 1 prueba |
