---
tipo: "modulo"
capa: "Infraestructura"
ruta: "engine/aispend.js"
lenguaje: "javascript"
lineas: 286
aliases: ["engine/aispend.js"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# engine/aispend.js

> Módulo · capa [[Capa Infraestructura]] · 286 líneas · `engine/aispend.js`

## Para qué sirve

💰 GASTO DE IA (🩺 Sistema → pestaña "Gasto IA")

## API pública (globales que define)

`window.KhipuSpend`

## Depende de

- [[app.html]] — usa `_tradeFetch`
- [[engine.app_main.js]] — usa `BASE`, `LANG`
- [[engine.toast.js]] — usa `khipuActor`

Se carga en [[app.html]] en la posición **59 de 98** (línea 3101), después de [[engine.committee.js]] y antes de [[engine.pfcommittee.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 59)
- [[engine.app_main.js]] — usa `KhipuSpend`

## Endpoints que llama

- `GET /api/ai/usage` → [[server.py]] ([[API ai]])
- `GET /api/decide/shadow` → [[core.decide_api.py]] ([[API decide]])
- `GET /api/decide/status` → [[core.decide_api.py]] ([[API decide]])
- `POST /api/ai/usage/limits` → [[server.py]] ([[API ai]])

## Pruebas que lo cubren

- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_jev_status_label.py]]
- [[tests.test_overnight_ui_small_panels.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-10-03 — GASTO DE IA, SIM. ESTRUCTURAL, AVATARES, CANVAS, COMITÉ DE CARTERA]]
