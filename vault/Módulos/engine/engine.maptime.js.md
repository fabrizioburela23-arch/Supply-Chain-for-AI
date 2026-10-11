---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "engine/maptime.js"
lenguaje: "javascript"
lineas: 389
aliases: ["engine/maptime.js"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# engine/maptime.js

> Módulo · capa [[Capa Ontología y grafo temporal]] · 389 líneas · `engine/maptime.js`

## Para qué sirve

EL TIEMPO DENTRO DEL MAPA PRINCIPAL (2026-09-25) Fabrizio: "el grafo temporal y el normal deberían ser uno; el temporal no da mucho por sí solo". Antes el tiempo vivía en una pestaña aparte con su propio grafo pequeño. Ahora el MISMO mapa de 949 nodos tiene:

## API pública (globales que define)

`window.KhipuMapTime`, `window.__tkgShow`, `window._mapTimePaint`

## Depende de

- [[app.html]] — usa `LANG`, `LINKS`, `NODE_BY_ID`, `_mapLayers`, `computeNodeRadius`, `getLinkColorHex`, `jumpTo`, `refreshStyles`, `selectNode`, `switchTab`
- [[engine.temporal-graph.js]] — usa `__tkgSetDate`, `initTKGTab`
- [[nodes.nodes_seed.js]] — usa `NODE_META`
- [[nodes.ontology.js]] — usa `ONTOLOGY`
- [[nodes.ontology_facts.js]] — usa `TEMPORAL_SEED_FACTS`
- [[nodes.temporal_seed_facts.js]] — usa `TEMPORAL_SEED_FACTS`
- [[nodes.temporal_seed_facts2.js]] — usa `TEMPORAL_SEED_FACTS`

Se carga en [[app.html]] en la posición **45 de 91** (línea 7829), después de [[engine.timeline3d.js]] y antes de [[engine.khipu_lang.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 45)
- [[app.html]] — usa `KhipuMapTime`, `_mapTimePaint`
- [[engine.khipu_lang.js]] — usa `KhipuMapTime`

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-25 — El Grafo Temporal se fusiona con el mapa principal]]
