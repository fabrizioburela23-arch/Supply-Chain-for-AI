---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/toast.js"
lenguaje: "javascript"
lineas: 640
aliases: ["engine/toast.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/toast.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 640 líneas · `engine/toast.js`

## Para qué sirve

NOTIFICACIONES y CONFIRMACIÓN de órdenes (pedido de Fabrizio 2026-10-02: "que te avise cuando estás comprando con una notificación pop up o vendiendo").

## API pública (globales que define)

`window.KhipuToast`

## Depende de

- [[app.html]] — usa `LANG`, `_tradeFetch`, `_tradeStatusInfo`

Se carga en [[app.html]] en la posición **27 de 93** (línea 7800), después de [[engine.loading.js]] y antes de [[engine.mascot.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 27)
- [[app.html]] — usa `KhipuToast`
- [[engine.clients.js]] — usa `KhipuToast`
- [[engine.cockpit.js]] — usa `KhipuToast`
- [[engine.committee.js]] — usa `KhipuToast`
- [[engine.crypto.js]] — usa `KhipuToast`
- [[engine.desktop.js]] — usa `KhipuToast`
- [[engine.pfcommittee.js]] — usa `KhipuToast`
- [[engine.pfreports.js]] — usa `KhipuToast`
- [[engine.portfolios.js]] — usa `KhipuToast`
- [[engine.reconcile.js]] — usa `KhipuToast`
- [[engine.voice.js]] — usa `KhipuToast`

## Endpoints que llama

- `GET /api/trade/history` → [[server.py]] ([[API trade]])

## Pruebas que lo cubren

- [[tests.test_overnight3_mic_voice_state.py]]
- [[tests.test_overnight3_toast_tokens.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-10-03 (c) — TERMINAL REDISEÑADA + POP-UPS DE COMPRA-VENTA (sw v182)]]
