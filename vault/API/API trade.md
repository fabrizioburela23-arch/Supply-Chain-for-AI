---
tipo: "api"
capa: "Dinero (carteras, trading, corretaje)"
rutas: 12
tags: ["capa/dinero", "tipo/api"]
---

# API trade

> 12 rutas · definidas en [[core.trading_agent.py]], [[server.py]] · prefijo `/api/trade`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/trade/account` | `trade_account` | [[server.py]] | [[app.html]], [[engine.trade.js]], 1 prueba |
| `POST` | `/api/trade/agent/config` | `agent_config` | [[core.trading_agent.py]] | 2 pruebas |
| `POST` | `/api/trade/agent/start` | `agent_start` | [[core.trading_agent.py]] | [[app.html]], 3 pruebas |
| `GET` | `/api/trade/agent/status` | `agent_status` | [[core.trading_agent.py]] | [[app.html]], 3 pruebas |
| `POST` | `/api/trade/agent/stop` | `agent_stop` | [[core.trading_agent.py]] | [[app.html]], 2 pruebas |
| `POST` | `/api/trade/close` | `trade_close` | [[server.py]] | [[engine.cockpit.js]], 2 pruebas |
| `GET` | `/api/trade/crypto/assets` | `trade_crypto_assets` | [[server.py]] | [[engine.crypto.js]], [[engine.trade.js]] |
| `GET` | `/api/trade/diag` | `trade_diag` | [[server.py]] | — |
| `GET` | `/api/trade/history` | `trade_history` | [[server.py]] | [[app.html]], [[engine.cockpit.js]], [[engine.toast.js]], 2 pruebas |
| `POST` | `/api/trade/order` | `trade_order` | [[server.py]] | [[app.html]], [[engine.crypto.js]], [[engine.trade.js]], 2 pruebas |
| `GET` | `/api/trade/positions/detail` | `trade_positions_detail` | [[server.py]] | [[app.html]], [[engine.cockpit.js]], [[engine.pfcommittee.js]], [[engine.voice.js]], 2 pruebas |
| `GET` | `/api/trade/status` | `trade_status` | [[server.py]] | [[app.html]], 1 prueba |
