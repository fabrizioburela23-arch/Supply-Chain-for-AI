---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "engine/app_preflight.js"
lenguaje: "javascript"
lineas: 142
aliases: ["engine/app_preflight.js"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# engine/app_preflight.js

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 142 líneas · `engine/app_preflight.js`

## Para qué sirve

Preflight debounce wiring

## API pública (globales que define)

`window.initSimTab`

## Depende de

- [[engine.app_coordinator.js]] — usa `initSimTab`
- [[engine.app_main.js]] — usa `LINKS`, `MKT`, `NODE_BY_ID`, `computeNRS`, `jumpTo`, `switchTab`
- [[nodes.nodes_seed.js]] — usa `NODES`

Se carga en [[app.html]] en la posición **99 de 101** (línea 3529), después de [[engine.app_trade_panel.js]] y antes de [[engine.app_canvas.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 99)

## Endpoints que llama

- `POST /api/ai/analyze` → [[server.py]] ([[API ai]])

## Pruebas que lo cubren

- [[tests.test_app_split.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (m) — app.html PARTIDO + 2 arreglos visibles — sw v268]]
- [[Sesión 2026-10-13 (l) — APP.HTML PARTIDO SIN CAMBIAR NADA (G5-06) — sw v267]]
