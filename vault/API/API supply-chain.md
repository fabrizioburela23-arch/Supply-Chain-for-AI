---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 1
tags: ["capa/datos-vivo", "tipo/api"]
---

# API supply-chain

> 1 rutas · definidas en [[server.py]] · prefijo `/api/supply-chain`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/supply-chain/trade-flows` | `trade_flows` | [[server.py]] | [[engine.app_coordinator.js]] |
