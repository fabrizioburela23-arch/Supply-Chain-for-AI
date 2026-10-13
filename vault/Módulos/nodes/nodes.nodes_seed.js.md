---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/nodes_seed.js"
lenguaje: "javascript"
lineas: 2661
aliases: ["nodes/nodes_seed.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/nodes_seed.js

> Datos · capa [[Capa Datos del catálogo]] · 2.661 líneas · `nodes/nodes_seed.js`

## Para qué sirve

DATOS SEMILLA (extraídos de app.html, 2026-07) Catálogo base v7/v8: categorías, países, 137 nodos seed, 546 links seed, metadatos por empresa, aliases de ids y tablas laterales de mercado. Se carga ANTES que los demás nodes_\*.js y del bloque inline principal; los const declarados aquí son visibles en todos los &lt;script> clásicos. Regla: los DATOS viven en nodes/, no en app.html.

## Qué datos contiene

- ~546 filas de vínculos (`[origen, destino, …]` o `{s, t}`)
- ~369 entradas con clave
- 293 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

De nivel superior (globales del script): `CATS`, `CATS_NEW`, `CAT_TO_SECTOR`, `COUNTRIES`, `INVEST_PATH`, `LOGO_DOMAIN`, `NODES`, `NODE_ID_ALIAS`, `NODE_META`, `RAW_LINKS`, `SECTORS9`, `SHARES_OUTSTANDING_B`, `sectorOf`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **2 de 95** (línea 1437) y antes de [[nodes.nodes_expand.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 2)
- [[app.html]] — usa `CATS`, `CATS_NEW`, `CAT_TO_SECTOR`, `COUNTRIES`, `INVEST_PATH`, `LOGO_DOMAIN`, `NODES`, `NODE_ID_ALIAS` y 4 más
- [[engine.brief.js]] — usa `NODES`
- [[engine.canvas-data.js]] — usa `NODES`
- [[engine.cockpit.js]] — usa `CAT_TO_SECTOR`, `NODES`, `NODE_META`, `SECTORS9`
- [[engine.command_center.js]] — usa `NODES`
- [[engine.compare.js]] — usa `CAT_TO_SECTOR`, `NODES`, `NODE_META`, `SECTORS9`
- [[engine.fincard.js]] — usa `NODES`, `NODE_META`
- [[engine.globe.js]] — usa `NODES`
- [[engine.graph3d.js]] — usa `CATS`
- [[engine.guide.js]] — usa `NODES`
- [[engine.insights.js]] — usa `CAT_TO_SECTOR`, `NODES`, `SECTORS9`
- [[engine.livesim.js]] — usa `CAT_TO_SECTOR`, `NODES`, `NODE_META`, `SECTORS9`
- [[engine.localcharts.js]] — usa `CAT_TO_SECTOR`, `NODES`, `NODE_META`, `SECTORS9`
- [[engine.maptime.js]] — usa `NODE_META`
- [[engine.matrixview.js]] — usa `CAT_TO_SECTOR`, `NODES`, `SECTORS9`
- [[engine.oswindows.js]] — usa `NODES`
- [[engine.pickers.js]] — usa `NODES`
- [[engine.portfolios.js]] — usa `NODES`, `NODE_META`
- [[engine.resolve.js]] — usa `NODES`, `NODE_ID_ALIAS`
- [[engine.riskreport.js]] — usa `NODES`
- [[engine.secondbrain.js]] — usa `NODES`, `NODE_META`
- [[engine.spacemonitor.js]] — usa `NODES`, `NODE_META`, `sectorOf`
- [[engine.statematrix.js]] — usa `CAT_TO_SECTOR`, `NODES`
- [[engine.temporal-graph.js]] — usa `NODE_META`
- [[engine.termdata.js]] — usa `NODES`, `NODE_META`
- [[engine.universe2d.js]] — usa `CATS`, `CAT_TO_SECTOR`, `SECTORS9`
- [[engine.voice.js]] — usa `CAT_TO_SECTOR`, `NODES`, `NODE_META`, `SECTORS9`
- [[engine.worldmonitor.js]] — usa `NODES`
- [[engine.xray.js]] — usa `CAT_TO_SECTOR`, `NODES`, `NODE_META`, `SECTORS9`
- [[nodes.meta_fill.js]] — usa `NODE_META`
- [[nodes.nodes_china.js]] — usa `NODE_META`
- [[nodes.nodes_expand5.js]] — usa `CATS_NEW`, `CAT_TO_SECTOR`, `NODE_META`
- [[nodes.nodes_multicapa.js]] — usa `CATS`, `CATS_NEW`, `CAT_TO_SECTOR`, `NODE_META`, `SECTORS9`
- [[sim.scenario_builder.js]] — usa `NODE_META`
- [[scripts.build_graph_review.py]] — lo nombra por su ruta
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

- [[tests.test_graph_audit.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (gg) — DIRECCIONES AL REVÉS + PESO DE LICENCIAS + PISO DEL KERNEL]]
- [[Sesión 2026-07-06 — Etapa 2 — Datos limpios - COMPLETA (5 batches publicados)]]
