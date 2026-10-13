---
tipo: "modulo"
capa: "Infraestructura"
ruta: "engine/aispend.js"
lenguaje: "javascript"
lineas: 283
aliases: ["engine/aispend.js"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# engine/aispend.js

> Módulo · capa [[Capa Infraestructura]] · 283 líneas · `engine/aispend.js`

## Para qué sirve

💰 GASTO DE IA (🩺 Sistema → pestaña "Gasto IA")

## API pública (globales que define)

`window.KhipuSpend`

## Depende de

- [[app.html]] — usa `BASE`, `LANG`, `_tradeFetch`
- [[engine.toast.js]] — usa `khipuActor`

Se carga en [[app.html]] en la posición **58 de 96** (línea 7918), después de [[engine.committee.js]] y antes de [[engine.pfcommittee.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 58)
- [[app.html]] — usa `KhipuSpend`

## Endpoints que llama

- `GET /api/ai/usage` → [[server.py]] ([[API ai]])
- `GET /api/decide/shadow` → [[core.decide_api.py]] ([[API decide]])
- `GET /api/decide/status` → [[core.decide_api.py]] ([[API decide]])
- `POST /api/ai/usage/limits` → [[server.py]] ([[API ai]])

## Pruebas que lo cubren

- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_overnight_ui_small_panels.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-10-03 — GASTO DE IA, SIM. ESTRUCTURAL, AVATARES, CANVAS, COMITÉ DE CARTERA]]
