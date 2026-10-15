---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/toast.js"
lenguaje: "javascript"
lineas: 767
aliases: ["engine/toast.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/toast.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 767 líneas · `engine/toast.js`

## Para qué sirve

NOTIFICACIONES y CONFIRMACIÓN de órdenes (pedido de Fabrizio 2026-10-02: "que te avise cuando estás comprando con una notificación pop up o vendiendo").

## API pública (globales que define)

`window.KhipuToast`, `window.khipuActor`

## Depende de

- [[app.html]] — usa `_tradeFetch`, `_tradeStatusInfo`
- [[engine.app_main.js]] — usa `LANG`

Se carga en [[app.html]] en la posición **29 de 100** (línea 3086), después de [[engine.loading.js]] y antes de [[engine.hotclient.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 29)
- [[app.html]] — usa `KhipuToast`
- [[engine.aispend.js]] — usa `khipuActor`
- [[engine.app_coordinator.js]] — usa `KhipuToast`
- [[engine.app_main.js]] — usa `khipuActor`
- [[engine.app_trade_panel.js]] — usa `KhipuToast`
- [[engine.clients.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.cockpit.js]] — usa `KhipuToast`
- [[engine.committee.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.crypto.js]] — usa `KhipuToast`
- [[engine.desktop.js]] — usa `KhipuToast`
- [[engine.genui.js]] — usa `KhipuToast`
- [[engine.governance.js]] — usa `KhipuToast`
- [[engine.importer.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.khipu_chat.js]] — usa `khipuActor`
- [[engine.khipu_lang.js]] — usa `khipuActor`
- [[engine.livesim.js]] — usa `khipuActor`
- [[engine.mcpconnect.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.pfcommittee.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.pfreports.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.portfolios.js]] — usa `KhipuToast`
- [[engine.pricehist.js]] — usa `KhipuToast`
- [[engine.reconcile.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.research.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.temporal-graph.js]] — usa `khipuActor`
- [[engine.trade.js]] — usa `KhipuToast`
- [[engine.voice.js]] — usa `KhipuToast`

## Endpoints que llama

- `GET /api/trade/history` → [[server.py]] ([[API trade]])

## Pruebas que lo cubren

- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_genui_browser.py]]
- [[tests.test_import_panel_browser.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_overnight3_mic_voice_state.py]]
- [[tests.test_overnight3_toast_tokens.py]]
- [[tests.test_scenario_pnl_browser.py]]
- [[tests.test_voice_os_client.py]]
- [[tests.test_voice_tour_client.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 (b) — LIMPIEZA QUE NO QUEDEN COSAS SUELTAS (sw v254)]]
- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-10-03 (c) — TERMINAL REDISEÑADA + POP-UPS DE COMPRA-VENTA (sw v182)]]
