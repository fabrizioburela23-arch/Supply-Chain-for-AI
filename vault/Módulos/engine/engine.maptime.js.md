---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "engine/maptime.js"
lenguaje: "javascript"
lineas: 525
aliases: ["engine/maptime.js"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# engine/maptime.js

> Módulo · capa [[Capa Ontología y grafo temporal]] · 525 líneas · `engine/maptime.js`

## Para qué sirve

EL TIEMPO DENTRO DEL MAPA PRINCIPAL (2026-09-25) Fabrizio: "el grafo temporal y el normal deberían ser uno; el temporal no da mucho por sí solo". Antes el tiempo vivía en una pestaña aparte con su propio grafo pequeño. Ahora el MISMO mapa de 949 nodos tiene:

## API pública (globales que define)

`window.KhipuMapTime`, `window.__tkgShow`, `window._mapTimePaint`

## Depende de

- [[engine.app_main.js]] — usa `BASE`, `LANG`, `LINKS`, `NODE_BY_ID`, `_mapLayers`, `computeNodeRadius`, `getLinkColorHex`, `jumpTo`, `refreshStyles`, `selectNode` y 1 más
- [[engine.temporal-graph.js]] — usa `__tkgSetDate`, `initTKGTab`
- [[nodes.ontology.js]] — usa `ONTOLOGY`
- [[nodes.ontology_facts.js]] — usa `TEMPORAL_SEED_FACTS`
- [[nodes.temporal_seed_facts.js]] — usa `TEMPORAL_SEED_FACTS`
- [[nodes.temporal_seed_facts2.js]] — usa `TEMPORAL_SEED_FACTS`

Se carga en [[app.html]] en la posición **52 de 104** (línea 3138), después de [[engine.timeline3d.js]] y antes de [[engine.khipu_lang.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 52)
- [[engine.app_main.js]] — usa `KhipuMapTime`, `_mapTimePaint`
- [[engine.khipu_lang.js]] — usa `KhipuMapTime`

## Endpoints que llama

- `GET /api/ontology/graph` → [[ontology.api.py]] ([[API ontology]])

## Pruebas que lo cubren

- [[tests.test_maptime_asof.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-25 — El Grafo Temporal se fusiona con el mapa principal]]
