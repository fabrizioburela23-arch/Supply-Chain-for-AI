---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "engine/temporal-graph.js"
lenguaje: "javascript"
lineas: 1466
aliases: ["engine/temporal-graph.js"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# engine/temporal-graph.js

> Módulo · capa [[Capa Ontología y grafo temporal]] · 1.466 líneas · `engine/temporal-graph.js`

## Para qué sirve

Grafo de Conocimiento Temporal (Khipus AI Finance) Reemplaza la vista 3D. Cada hecho tiene ventana de validez (valid_from → valid_until). Un timeline deslizable/reproducible muestra cómo las relaciones aparecen, están vigentes o expiran a lo largo del tiempo. Funciona 100% client-side (deriva de TEMPORAL_SEED_FACTS + LINKS + PREIPO_INTEL); la historia con fecha vive en Postgres (ontología bitemporal). Expone window.initTKGTab.

## API pública (globales que define)

`window.__tkgOpenObj`, `window.__tkgSetDate`, `window.initTKGTab`

## Depende de

- [[app.html]] — usa `_tradeErrText`, `_tradeFetch`, `safeUrl`
- [[engine.app_main.js]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `SERVER_MODE`, `catLabel`, `computeNRS`, `fetchQuotes`, `getCatColorHex` y 2 más
- [[engine.geo_coords.js]] — usa `GeoCoords`, `KhipuCountries`
- [[engine.timeline3d.js]] — usa `KhipuTimeline3D`
- [[engine.toast.js]] — usa `khipuActor`
- [[nodes.nodes_seed.js]] — usa `NODE_META`
- [[nodes.ontology.js]] — usa `ONTOLOGY`
- [[nodes.ontology_facts.js]] — usa `TEMPORAL_SEED_FACTS`
- [[nodes.preipo_intel.js]] — usa `PREIPO_INTEL`
- [[nodes.temporal_seed_facts.js]] — usa `TEMPORAL_SEED_FACTS`
- [[nodes.temporal_seed_facts2.js]] — usa `TEMPORAL_SEED_FACTS`

Se carga en [[app.html]] en la posición **50 de 104** (línea 3136), después de [[nodes.legal_names.js]] y antes de [[engine.timeline3d.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 50)
- [[engine.app_main.js]] — usa `initTKGTab`
- [[engine.cockpit.js]] — usa `__tkgOpenObj`, `initTKGTab`
- [[engine.command_center.js]] — usa `__tkgOpenObj`
- [[engine.khipu_lang.js]] — usa `__tkgSetDate`
- [[engine.maptime.js]] — usa `__tkgSetDate`, `initTKGTab`
- [[engine.xray.js]] — usa `__tkgOpenObj`

## Endpoints que llama

- `GET /api/grafo/estado` → [[server.py]] ([[API grafo]])
- `GET /api/news/<ticker>` → [[server.py]] ([[API news]])
- `GET /api/news/gdelt/<company_name>` → [[server.py]] ([[API news]])
- `GET /api/ontology/objects/<object_id>/timeline` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/objects/<object_id>` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/status` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ai/analyze` → [[server.py]] ([[API ai]])
- `POST /api/news/portfolio` → [[core.portfolio_reports_api.py]] ([[API news]])
- `POST /api/ontology/actions/<action_type>` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/ingest/news` → [[ontology.api.py]] ([[API ontology]])

## Pruebas que lo cubren

- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_countries.py]]
- [[tests.test_lotek_fixer.py]]
- [[tests.test_neo4j_retirado.py]]
- [[tests.test_review_infra_c.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (i) — NEO4J RETIRADO (decisión 6 de Fabrizio) — sw v264]]
- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
