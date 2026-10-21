---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "engine/localcharts.js"
lenguaje: "javascript"
lineas: 1696
aliases: ["engine/localcharts.js"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# engine/localcharts.js

> Módulo · capa [[Capa Chat y agentes]] · 1.696 líneas · `engine/localcharts.js`

## Para qué sirve

CANVAS: ROUTER DE INTENCIÓN + GRÁFICOS SIN IA (Etapa G 2026-07-11 · Etapa I 2026-07-12 · ROUTER 2026-10-02)

## API pública (globales que define)

`window.KhipuLocalCharts`, `window.__khlcFetchWrapped`, `window.fetch`, `window.switchTab`

## Depende de

- [[engine.app_canvas.js]] — usa `cvCol`
- [[engine.app_main.js]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `_selectedNode`, `computeNRS`, `computeNRSBreakdown`, `quotePx`, `switchTab`
- [[engine.cockpit.js]] — usa `BixbyCockpit`
- [[engine.pfcommittee.js]] — usa `KhipuPortfolioCommittee`
- [[engine.resolve.js]] — usa `KhipuResolve`
- [[nodes.nodes_seed.js]] — usa `CAT_TO_SECTOR`, `NODES`, `NODE_META`, `SECTORS9`

Se carga en [[app.html]] en la posición **78 de 103** (línea 3203), después de [[engine.nav4.js]] y antes de [[engine.fincard.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 78)
- [[engine.app_canvas.js]] — usa `KhipuLocalCharts`
- [[engine.cockpit.js]] — usa `KhipuLocalCharts`

## Endpoints que llama

- `GET /api/candles/<ticker>` → [[server.py]] ([[API candles]])
- `GET /api/crypto/<coin_id>/history` → [[server.py]] ([[API crypto]])
- `GET /api/crypto/<coin_id>` → [[server.py]] ([[API crypto]])
- `GET /api/crypto/markets` → [[server.py]] ([[API crypto]])
- `GET /api/findossier/<ticker>` → [[server.py]] ([[API findossier]])
- `POST /api/crypto/analyze` → [[server.py]] ([[API crypto]])

## Pruebas que lo cubren

- [[tests.js.localcharts_intents.js]]
- [[tests.js.localcharts_pfperf.js]]
- [[tests.test_canvas_charts.py]]
- [[tests.test_localcharts_intents.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (dd) — RENDIMIENTO DE MI CARTERA COMO GRÁFICO SIN IA (sw v238-v239)]]
- [[Sesión 2026-10-05 (cc) — GRÁFICOS - DATOS EN VIVO + MÁS PREGUNTAS SIN IA (sw v237)]]
- [[Sesión 2026-10-03 — GASTO DE IA, SIM. ESTRUCTURAL, AVATARES, CANVAS, COMITÉ DE CARTERA]]
- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
