---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "engine/app_trade_panel.js"
lenguaje: "javascript"
lineas: 608
aliases: ["engine/app_trade_panel.js"]
tags: ["capa/dinero", "tipo/modulo"]
---

# engine/app_trade_panel.js

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 608 líneas · `engine/app_trade_panel.js`

## Para qué sirve

Professional Trade Panel

## API pública (globales que define)

`window.__tradeAcctCache`, `window._tpRefreshAgentStatus`, `window._tpRefreshBlotter`, `window._tpRefreshPositions`, `window._tpRelabel`, `window.closeTradePanelFn`, `window.openTradeModal`, `window.openTradePanelFn`, `window.setTradePanelQtyPct`, `window.setTradePanelSide`, `window.submitTradePanelOrder`, `window.toggleTradingAgent`, `window.updateTradePanelRisk`

## Depende de

- [[app.html]] — usa `_tradeErrText`, `_tradeFetch`, `_tradeOrderAmbiguous`, `_tradeOrderId`, `_tradeOrderIsDup`, `_tradeOrderResolve`, `_tradeOrderSettle`, `_tradeStatusInfo`
- [[engine.app_main.js]] — usa `LANG`, `MKT`, `activeTab`, `applyLang`, `esc`, `quotePx`, `renderMarket`, `savePos`
- [[engine.toast.js]] — usa `KhipuToast`
- [[nodes.nodes_seed.js]] — usa `NODES`

Se carga en [[app.html]] en la posición **94 de 97** (línea 3452), después de [[engine.app_coordinator.js]] y antes de [[engine.app_preflight.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 94)
- [[app.html]] — usa `_tpRefreshAgentStatus`, `_tpRefreshBlotter`, `_tpRefreshPositions`, `closeTradePanelFn`, `setTradePanelQtyPct`, `setTradePanelSide`, `submitTradePanelOrder`, `toggleTradingAgent` y 1 más
- [[engine.app_coordinator.js]] — usa `openTradeModal`
- [[engine.app_main.js]] — usa `openTradeModal`
- [[engine.resolve.js]] — usa `openTradeModal`
- [[engine.voice.js]] — usa `__tradeAcctCache`, `openTradeModal`

## Endpoints que llama

- `GET /api/candles/<ticker>` → [[server.py]] ([[API candles]])
- `GET /api/trade/account` → [[server.py]] ([[API trade]])
- `GET /api/trade/agent/status` → [[core.trading_agent.py]] ([[API trade]])
- `GET /api/trade/history` → [[server.py]] ([[API trade]])
- `GET /api/trade/positions/detail` → [[server.py]] ([[API trade]])
- `POST /api/trade/agent/start` → [[core.trading_agent.py]] ([[API trade]])
- `POST /api/trade/agent/stop` → [[core.trading_agent.py]] ([[API trade]])
- `POST /api/trade/order` → [[server.py]] ([[API trade]])

## Pruebas que lo cubren

- [[tests.test_app_split.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (m) — app.html PARTIDO + 2 arreglos visibles — sw v268]]
- [[Sesión 2026-10-13 (l) — APP.HTML PARTIDO SIN CAMBIAR NADA (G5-06) — sw v267]]
