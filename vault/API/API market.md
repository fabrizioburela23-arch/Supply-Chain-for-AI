---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 4
tags: ["capa/datos-vivo", "tipo/api"]
---

# API market

> 4 rutas · definidas en [[server.py]] · prefijo `/api/market`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/market/live_caps` | `market_live_caps` | [[server.py]] | [[engine.app_main.js]], 1 prueba |
| `GET` | `/api/market/live_fundamentals` | `market_live_fundamentals` | [[server.py]] | [[engine.app_main.js]] |
| `GET` | `/api/market/providers` | `market_providers` | [[server.py]] | 2 pruebas |
| `GET` | `/api/market/quote/<path:symbol>` | `market_quote` | [[server.py]] | 1 prueba |
