---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "engine/resolve.js"
lenguaje: "javascript"
lineas: 497
aliases: ["engine/resolve.js"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# engine/resolve.js

> Módulo · capa [[Capa Chat y agentes]] · 497 líneas · `engine/resolve.js`

## Para qué sirve

RESOLUTOR DE EMPRESAS + SUPERFICIE DE RESULTADOS (2026-07) Feedback real de Fabrizio: "bixby a veces me dice que una empresa no existe o no me entiende, especialmente con nvidia" y "le pido algo y no me muestra y es pq esta atras del interfaz".

## API pública (globales que define)

`window.KhipuResolve`, `window._surface`

## Depende de

- [[app.html]] — usa `LANG`, `NODE_BY_ID`, `_openSecondBrain`, `_termOpenTicker`, `activateStress`, `canvasGenerate`, `closeSistema`, `jumpTo`, `loadStockChart`, `openTradeModal` y 1 más
- [[engine.cockpit.js]] — usa `BixbyCockpit`
- [[engine.compare.js]] — usa `openCompare`
- [[engine.fincard.js]] — usa `openFinCard`
- [[engine.insights.js]] — usa `renderKhipuInsights`
- [[engine.voice.js]] — usa `_openBrokerStage`
- [[engine.xray.js]] — usa `openXRay`
- [[nodes.legal_names.js]] — usa `LEGAL_NAMES`
- [[nodes.nodes_seed.js]] — usa `NODES`, `NODE_ID_ALIAS`

Se carga en [[app.html]] en la posición **32 de 92** (línea 7816), después de [[engine.universe2d.js]] y antes de [[engine.orb.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 32)
- [[app.html]] — usa `KhipuResolve`, `_surface`
- [[engine.brief.js]] — usa `_surface`
- [[engine.cockpit.js]] — usa `KhipuResolve`, `_surface`
- [[engine.command_center.js]] — usa `KhipuResolve`, `_surface`
- [[engine.crypto.js]] — usa `_surface`
- [[engine.fincard.js]] — usa `KhipuResolve`
- [[engine.khipu_chat.js]] — usa `KhipuResolve`, `_surface`
- [[engine.khipu_lang.js]] — usa `KhipuResolve`
- [[engine.localcharts.js]] — usa `KhipuResolve`
- [[engine.oswindows.js]] — usa `KhipuResolve`
- [[engine.pfcommittee.js]] — usa `_surface`
- [[engine.pickers.js]] — usa `KhipuResolve`
- [[engine.portfolios.js]] — usa `KhipuResolve`
- [[engine.spacemonitor.js]] — usa `_surface`
- [[engine.voice.js]] — usa `KhipuResolve`, `_surface`
- [[engine.worldmonitor.js]] — usa `_surface`
- [[engine.xray.js]] — usa `_surface`

## Pruebas que lo cubren

- [[tests.test_khipus_os_integration.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (ii) — KHIPUS OS v1 (sw v245)]]
- [[Sesión 2026-09-27 (b) — Nombres - búsqueda por nombre legal + etiquetas legibles (sw v137)]]
- [[Sesión 2026-07-12 — Etapas I+J — Feedback 8 + Expediente Cripto (sw v76)]]
