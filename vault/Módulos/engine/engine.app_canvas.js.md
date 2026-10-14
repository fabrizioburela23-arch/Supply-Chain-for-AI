---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "engine/app_canvas.js"
lenguaje: "javascript"
lineas: 688
aliases: ["engine/app_canvas.js"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# engine/app_canvas.js

> Módulo · capa [[Capa Chat y agentes]] · 688 líneas · `engine/app_canvas.js`

## Para qué sirve

palette & helpers

## API pública (globales que define)

`window._cvRenderCard`, `window.canvasGenerate`, `window.cvCol`, `window.initCanvasTab`

## Depende de

- [[engine.app_main.js]] — usa `LANG`, `MKT`, `_selectedNode`, `computeNRS`
- [[engine.canvas-data.js]] — usa `canvasEnrichData`
- [[engine.localcharts.js]] — usa `KhipuLocalCharts`
- [[nodes.nodes_seed.js]] — usa `NODES`

Se carga en [[app.html]] en la posición **98 de 99** (línea 3528), después de [[engine.app_preflight.js]] y antes de [[engine.app_scatter.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 98)
- [[app.html]] — usa `canvasGenerate`
- [[engine.app_main.js]] — usa `initCanvasTab`
- [[engine.cockpit.js]] — usa `_cvRenderCard`
- [[engine.command_center.js]] — usa `_cvRenderCard`, `canvasGenerate`
- [[engine.genui_charts.js]] — usa `cvCol`
- [[engine.localcharts.js]] — usa `cvCol`
- [[engine.resolve.js]] — usa `canvasGenerate`

## Endpoints que llama

- `POST /api/canvas/generate` → [[server.py]] ([[API canvas]])

## Pruebas que lo cubren

- [[tests.test_app_split.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (m) — app.html PARTIDO + 2 arreglos visibles — sw v268]]
- [[Sesión 2026-10-13 (l) — APP.HTML PARTIDO SIN CAMBIAR NADA (G5-06) — sw v267]]
