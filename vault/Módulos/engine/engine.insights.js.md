---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "engine/insights.js"
lenguaje: "javascript"
lineas: 360
aliases: ["engine/insights.js"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# engine/insights.js

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 360 líneas · `engine/insights.js`

## Para qué sirve

INSIGHTS AUTOMÁTICOS (Etapa 5, piel NEXUS) Genera tarjetas de lectura desde la topología + el motor de matrices: - chokepoints (quién arrastra a más empresas si cae) - riesgo alto (NRS) — con foco en tu cartera - factores externos activos (hiperaristas) - concentración geográfica

## API pública (globales que define)

`window._insJump`, `window._insShock`, `window.renderInsightsHistory`, `window.renderKhipuInsights`

## Depende de

- [[app.html]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `activateStress`, `computeDownstream`, `computeNRS`, `jumpTo`, `sectorName` y 1 más
- [[engine.xray.js]] — usa `openXRay`
- [[nodes.nodes_seed.js]] — usa `CAT_TO_SECTOR`, `NODES`, `SECTORS9`

Se carga en [[app.html]] en la posición **64 de 92** (línea 7914), después de [[engine.mcpconnect.js]] y antes de [[engine.statematrix.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 64)
- [[app.html]] — usa `renderInsightsHistory`, `renderKhipuInsights`
- [[engine.live.js]] — usa `renderKhipuInsights`
- [[engine.resolve.js]] — usa `renderKhipuInsights`

## Endpoints que llama

- `GET /api/matrix/<rel_type>` → [[matrix.api.py]] ([[API matrix]])
- `GET /api/matrix/insights/history` → [[matrix.api.py]] ([[API matrix]])
- `GET /api/matrix/metrics` → [[matrix.api.py]] ([[API matrix]])
- `GET /api/matrix/status` → [[matrix.api.py]] ([[API matrix]])

## Pruebas que lo cubren

- [[tests.test_live_labels_misc.py]]
- [[tests.test_overnight2_scenes_tokens.py]]
- [[tests.test_overnight_ui_small_panels.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-09-21 — Limpieza estructural - Track A Fase 2 + Track B completos]]
- [[Sesión 2026-07 — Ampliaciones (tras feedback simulaciones muy cerradas, más info)]]
