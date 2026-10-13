---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "engine/secondbrain.js"
lenguaje: "javascript"
lineas: 233
aliases: ["engine/secondbrain.js"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# engine/secondbrain.js

> Módulo · capa [[Capa Ontología y grafo temporal]] · 233 líneas · `engine/secondbrain.js`

## Para qué sirve

Second Brain de 5 capas para Khipu Finance Al seleccionar una empresa, abre un panel con 5 capas de conocimiento: 1. Mercado (precio + sparkline + NRS) 2. Noticias 3. Tesis (catalizadores + riesgos + IA) 4. Simulación (presets de escenario) 5. Red (betweenness + cascada + desglose NRS)

## API pública (globales que define)

`window.SecondBrain`

De nivel superior (globales del script): `_sbEn`, `_sbFlow`, `_sbL`

## Depende de

- [[app.html]] — usa `DataLayer`, `LANG`, `LINKS`, `NODE_BY_ID`, `NRS_FLOW_TYPES`, `V8detail`, `_secondBrain`, `activateStress`, `catColor`, `computeDownstream` y 11 más
- [[nodes.nodes_seed.js]] — usa `NODES`, `NODE_META`

Se carga en [[app.html]] en la posición **35 de 92** (línea 7828), después de [[engine.voice.js]] y antes de [[engine.geo_coords.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 35)
- [[app.html]] — usa `SecondBrain`

## Endpoints que llama

- `GET /api/candles/<ticker>` → [[server.py]] ([[API candles]])

## Pruebas que lo cubren

- [[tests.test_cleanup_client.py]]
- [[tests.test_server_smoke.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-07-05 — Etapa 1 — Limpieza masiva - COMPLETA (4 batches publicados)]]
