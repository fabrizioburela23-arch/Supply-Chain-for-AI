---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/timeline.py"
lenguaje: "python"
lineas: 331
aliases: ["ontology/timeline.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/timeline.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 331 líneas · `ontology/timeline.py`

## Para qué sirve

Phase 1 · M5: la línea de tiempo de una entidad.

## API pública

- `entity_timeline(session, object_id, limit=…, lang=…, include_news=…)` — Todo lo que le ha pasado a una entidad, en un solo hilo ordenado. _(línea 116)_
- `global_feed(session, limit=…, lang=…, since=…)` — Lo más reciente del grafo entero, más nuevo primero. _(línea 222)_

**Internas** (empiezan con `_`): `_iso`, `_titulo`

## Depende de

- [[ontology.ingest_news.py]] — importa `NEWS_TYPE`, `REPORTS_REL`, `news_for_object`
- [[ontology.models.py]] — importa `Event`, `LinkRecord`, `ObjectRecord`
- [[ontology.provenance.py]] — importa `source_to_dict`
- [[ontology.service.py]] — importa `is_genesis`

## Lo usan

- [[ontology.api.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_repair_graph.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-27 (c) — Feed global Lo último en el grafo (sw v138)]]
- [[Sesión 2026-09-22 al 24 — PHASE 1 Live Investment Graph COMPLETA + velocidad + 3D temporal]]
