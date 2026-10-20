---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "engine/trade.js"
lenguaje: "javascript"
lineas: 274
aliases: ["engine/trade.js"]
tags: ["capa/dinero", "tipo/modulo"]
---

# engine/trade.js

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 274 líneas · `engine/trade.js`

## Para qué sirve

TRADING COMPARTIDO del navegador (lote I4, G5-07: salió TAL CUAL de engine/voice.js). Lo usan la voz (engine/voice.js: place_order / get_account_status), la Cabina (engine/cockpit.js, ventana 'broker') y engine/command_center.js. Se carga ANTES de voice.js (app.html y SHELL de sw.js). Regla de oro del dinero: toda orden va por window._tradeFetch (PIN X-Trade-Pin) → POST /api/trade/order → brokerage.service (house_order). Nada de aquí envía sin confirmación explícita (clic o «sí» verbal).

## API pública (globales que define)

`window.__lastTradeExec`, `window.__tradeAcctCache`, `window.__tradeInflight`, `window._executeTradeOrder`, `window._openBrokerStage`, `window._resolveTradeSymbol`, `window._tradeAccountInfo`

## Depende de

- [[app.html]] — usa `_tradeErrText`, `_tradeFetch`, `_tradeOrderAmbiguous`, `_tradeOrderId`, `_tradeOrderIsDup`, `_tradeOrderSettle`
- [[engine.app_main.js]] — usa `LANG`
- [[engine.cockpit.js]] — usa `BixbyCockpit`
- [[engine.resolve.js]] — usa `KhipuResolve`
- [[engine.toast.js]] — usa `KhipuToast`

Se carga en [[app.html]] en la posición **38 de 102** (línea 3097), después de [[engine.orb.js]] y antes de [[engine.signals.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 38)
- [[engine.cockpit.js]] — usa `_executeTradeOrder`, `_openBrokerStage`, `_resolveTradeSymbol`, `_tradeAccountInfo`
- [[engine.resolve.js]] — usa `_openBrokerStage`
- [[engine.voice.js]] — usa `__tradeAcctCache`, `_executeTradeOrder`, `_openBrokerStage`, `_resolveTradeSymbol`, `_tradeAccountInfo`

## Endpoints que llama

- `GET /api/trade/account` → [[server.py]] ([[API trade]])
- `GET /api/trade/crypto/assets` → [[server.py]] ([[API trade]])
- `POST /api/trade/order` → [[server.py]] ([[API trade]])

## Pruebas que lo cubren

- [[tests.test_client_hardening.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_overnight_voice_client.py]]
- [[tests.test_voice_os_client.py]]
- [[tests.test_voice_tour_client.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (k) — FASE 2+ LOTE I - rutas con decisión, CSP estricta, riesgo]]
