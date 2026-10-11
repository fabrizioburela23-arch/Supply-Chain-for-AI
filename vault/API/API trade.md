---
tipo: "api"
capa: "Dinero (carteras, trading, corretaje)"
rutas: 12
tags: ["capa/dinero", "tipo/api"]
---

# API trade

> 12 rutas · definidas en [[server.py]] · prefijo `/api/trade`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/trade/account` | `trade_account` | [[server.py]] | [[app.html]], [[engine.voice.js]], 1 prueba |
| `POST` | `/api/trade/agent/config` | `agent_config` | [[server.py]] | 1 prueba |
| `POST` | `/api/trade/agent/start` | `agent_start` | [[server.py]] | [[app.html]], 1 prueba |
| `GET` | `/api/trade/agent/status` | `agent_status` | [[server.py]] | [[app.html]], 1 prueba |
| `POST` | `/api/trade/agent/stop` | `agent_stop` | [[server.py]] | [[app.html]], 1 prueba |
| `POST` | `/api/trade/close` | `trade_close` | [[server.py]] | [[engine.cockpit.js]], 1 prueba |
| `GET` | `/api/trade/crypto/assets` | `trade_crypto_assets` | [[server.py]] | [[engine.crypto.js]], [[engine.voice.js]] |
| `GET` | `/api/trade/diag` | `trade_diag` | [[server.py]] | — |
| `GET` | `/api/trade/history` | `trade_history` | [[server.py]] | [[app.html]], [[engine.cockpit.js]], [[engine.toast.js]], 2 pruebas |
| `POST` | `/api/trade/order` | `trade_order` | [[server.py]] | [[app.html]], [[engine.crypto.js]], [[engine.voice.js]], 1 prueba |
| `GET` | `/api/trade/positions/detail` | `trade_positions_detail` | [[server.py]] | [[app.html]], [[engine.cockpit.js]], [[engine.pfcommittee.js]], [[engine.voice.js]], 2 pruebas |
| `GET` | `/api/trade/status` | `trade_status` | [[server.py]] | [[app.html]], 1 prueba |
