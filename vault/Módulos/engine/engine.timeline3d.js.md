---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "engine/timeline3d.js"
lenguaje: "javascript"
lineas: 254
aliases: ["engine/timeline3d.js"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# engine/timeline3d.js

> Módulo · capa [[Capa Ontología y grafo temporal]] · 254 líneas · `engine/timeline3d.js`

## Para qué sirve

El Grafo Temporal en 3D, donde la PROFUNDIDAD ES EL TIEMPO.

## API pública (globales que define)

`window.KhipuTimeline3D`

## Depende de

- [[app.html]] — usa `LANG`, `NODE_BY_ID`, `getLinkColorHex`
- [[nodes.ontology_facts.js]] — usa `TEMPORAL_SEED_FACTS`
- [[nodes.temporal_seed_facts.js]] — usa `TEMPORAL_SEED_FACTS`
- [[nodes.temporal_seed_facts2.js]] — usa `TEMPORAL_SEED_FACTS`

Se carga en [[app.html]] en la posición **46 de 96** (línea 7855), después de [[engine.temporal-graph.js]] y antes de [[engine.maptime.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 46)
- [[engine.temporal-graph.js]] — usa `KhipuTimeline3D`

## Pruebas que lo cubren

- [[tests.test_server_smoke.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-22 al 24 — PHASE 1 Live Investment Graph COMPLETA + velocidad + 3D temporal]]
