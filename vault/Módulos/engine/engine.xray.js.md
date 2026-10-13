---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/xray.js"
lenguaje: "javascript"
lineas: 666
aliases: ["engine/xray.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/xray.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 666 líneas · `engine/xray.js`

## Para qué sirve

X-RAY DE EMPRESA · "desarmar el alma" (Etapa 4, wow #1) Overlay NEXUS-styled que abre para cualquier nodo: - anatomía (sector, país, precio en vivo, fundamentales) - NRS descompuesto término a término (auditabilidad Palantir) + ranking - los HILOS entrantes/salientes con peso, clicables → saltan al mapa - simulación de impacto con el motor ÚNICO del servidor (/api/hot/impact vía window.KhipuHot, precalculado: una sola cifra, la misma que la Cabina, la voz y el mapa; paso 13 INFRA_OPERATIVA)

## API pública (globales que define)

`window._xrayClose`, `window._xrayCompare`, `window._xrayJump`, `window._xrayShock`, `window._xrayTKG`, `window.buildXRayHTML`, `window.openXRay`, `window.wireXRay`, `window.xrayEnsureStyles`, `window.xrayImpact`

## Depende de

- [[app.html]] — usa `DataLayer`, `KhipuLive`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `_openSecondBrain`, `activateStress`, `computeNRS`, `computeNRSBreakdown` y 7 más
- [[engine.cockpit.js]] — usa `BixbyCockpit`
- [[engine.committee.js]] — usa `KhipuCommittee`
- [[engine.compare.js]] — usa `openCompare`
- [[engine.explain.js]] — usa `explainChip`, `explainMetric`
- [[engine.fincard.js]] — usa `openFinCard`
- [[engine.live.js]] — usa `KhipuLive`
- [[engine.mascot.js]] — usa `KhipuMascot`
- [[engine.research.js]] — usa `KhipuResearch`
- [[engine.resolve.js]] — usa `_surface`
- [[engine.temporal-graph.js]] — usa `__tkgOpenObj`
- [[nodes.nodes_seed.js]] — usa `CAT_TO_SECTOR`, `NODES`, `NODE_META`, `SECTORS9`

Se carga en [[app.html]] en la posición **50 de 95** (línea 7851), después de [[engine.guide.js]] y antes de [[engine.research.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 50)
- [[app.html]] — usa `openXRay`
- [[engine.cockpit.js]] — usa `buildXRayHTML`, `wireXRay`, `xrayEnsureStyles`
- [[engine.command_center.js]] — usa `openXRay`
- [[engine.insights.js]] — usa `openXRay`
- [[engine.khipu_chat.js]] — usa `openXRay`
- [[engine.oswindows.js]] — usa `openXRay`
- [[engine.resolve.js]] — usa `openXRay`
- [[engine.spacemonitor.js]] — usa `openXRay`
- [[engine.termdata.js]] — usa `openXRay`
- [[engine.voice.js]] — usa `openXRay`
- [[engine.worldmonitor.js]] — usa `openXRay`

## Endpoints que llama

- `GET /api/tensor/node/<path:nid>` → [[matrix.tensor_api.py]] ([[API tensor]])

## Pruebas que lo cubren

- [[tests.test_no_client_engine.py]]
- [[tests.test_overnight3_toast_tokens.py]]
- [[tests.test_overnight_ui_xray_research.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-09-28 — X-Ray pulido (sw v139)]]
- [[Sesión 2026-07 — Ampliaciones (tras feedback simulaciones muy cerradas, más info)]]
