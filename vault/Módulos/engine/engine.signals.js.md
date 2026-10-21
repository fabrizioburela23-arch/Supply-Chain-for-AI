---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/signals.js"
lenguaje: "javascript"
lineas: 172
aliases: ["engine/signals.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/signals.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 172 líneas · `engine/signals.js`

## Para qué sirve

«1 TOQUE»: señales del agente de trading listas para aprobar (2026-10-20) El agente en modo MANUAL propone (servidor: core/trading_agent.py, GET /api/trade/agent/signals): lado, monto, precio que vio, stop, confianza, RSI/tendencia/convicción y el motivo. Aquí se ven como tarjetas flotantes y: · cuenta de PAPEL 🧪 → un toque en «Comprar 500 USD» la envía; · DINERO REAL 🔴 → un toque + el diálogo de confirmación de siempre (KhipuToast.confirmOrder, casilla «entiendo»). La orden sale por POST /api/trade/agent/signals/&lt;id>/take (PIN por window._tradeFetch → EL camino único brokerage.service.house_order). El servidor la rechaza si venció (15 min) o si el precio se movió > 1,5 …

## API pública (globales que define)

`window.KhipuSignals`

## Depende de

- [[app.html]] — usa `_tradeFetch`, `_tradePinStored`
- [[engine.app_main.js]] — usa `LANG`, `NODE_BY_ID`
- [[engine.toast.js]] — usa `KhipuToast`

Se carga en [[app.html]] en la posición **39 de 103** (línea 3098), después de [[engine.trade.js]] y antes de [[engine.voice.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 39)

## Endpoints que llama

- `GET /api/trade/agent/signals` → [[core.trading_agent.py]] ([[API trade]])
- `POST /api/trade/agent/signals/<sid>/dismiss` → [[core.trading_agent.py]] ([[API trade]])
- `POST /api/trade/agent/signals/<sid>/take` → [[core.trading_agent.py]] ([[API trade]])

## Pruebas que lo cubren

- [[tests.test_agent_signals_one_tap.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
