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

- [[app.html]] — usa `LANG`, `_tradeFetch`, `_tradeStatusInfo`

Se carga en [[app.html]] en la posición **27 de 92** (línea 7811), después de [[engine.loading.js]] y antes de [[engine.agents_registry.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 27)
- [[app.html]] — usa `KhipuToast`, `khipuActor`
- [[engine.aispend.js]] — usa `khipuActor`
- [[engine.clients.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.cockpit.js]] — usa `KhipuToast`
- [[engine.committee.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.crypto.js]] — usa `KhipuToast`
- [[engine.desktop.js]] — usa `KhipuToast`
- [[engine.khipu_chat.js]] — usa `khipuActor`
- [[engine.khipu_lang.js]] — usa `khipuActor`
- [[engine.livesim.js]] — usa `khipuActor`
- [[engine.mcpconnect.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.pfcommittee.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.pfreports.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.portfolios.js]] — usa `KhipuToast`
- [[engine.reconcile.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.research.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.temporal-graph.js]] — usa `khipuActor`
- [[engine.voice.js]] — usa `KhipuToast`

## Endpoints que llama

- `GET /api/trade/history` → [[server.py]] ([[API trade]])

## Pruebas que lo cubren

- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_overnight3_mic_voice_state.py]]
- [[tests.test_overnight3_toast_tokens.py]]
- [[tests.test_voice_os_client.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 (b) — LIMPIEZA QUE NO QUEDEN COSAS SUELTAS (sw v254)]]
- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-10-03 (c) — TERMINAL REDISEÑADA + POP-UPS DE COMPRA-VENTA (sw v182)]]
