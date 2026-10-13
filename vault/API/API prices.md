---
tipo: "api"
capa: "Infraestructura"
rutas: 5
tags: ["capa/infraestructura", "tipo/api"]
---

# API prices

> 5 rutas · definidas en [[core.prices_api.py]] · prefijo `/api/prices`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/prices/backfill` | `prices_backfill_state` | [[core.prices_api.py]] | [[engine.pricehist.js]], 1 prueba |
| `POST` | `/api/prices/backfill` | `prices_backfill_start` | [[core.prices_api.py]] | [[engine.pricehist.js]], 1 prueba |
| `POST` | `/api/prices/backfill/stop` | `prices_backfill_stop` | [[core.prices_api.py]] | [[engine.pricehist.js]] |
| `GET` | `/api/prices/eod/<path:symbol>` | `prices_eod` | [[core.prices_api.py]] | — |
| `GET` | `/api/prices/status` | `prices_status` | [[core.prices_api.py]] | [[engine.pricehist.js]], 1 prueba |
