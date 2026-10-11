---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 4
tags: ["capa/datos-vivo", "tipo/api"]
---

# API crypto

> 4 rutas · definidas en [[server.py]] · prefijo `/api/crypto`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/crypto/<coin_id>` | `crypto_detail` | [[server.py]] | [[engine.crypto.js]], [[engine.localcharts.js]], 1 prueba |
| `GET` | `/api/crypto/<coin_id>/history` | `crypto_history` | [[server.py]] | [[engine.crypto.js]], [[engine.localcharts.js]] |
| `POST` | `/api/crypto/analyze` | `crypto_analyze` | [[server.py]] | [[engine.crypto.js]], [[engine.localcharts.js]] |
| `GET` | `/api/crypto/markets` | `crypto_markets` | [[server.py]] | [[engine.crypto.js]], [[engine.localcharts.js]], 1 prueba |
