---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/ingest_news.py"
lenguaje: "python"
lineas: 205
aliases: ["ontology/ingest_news.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/ingest_news.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 205 líneas · `ontology/ingest_news.py`

## Para qué sirve

Phase 1 · M4: las noticias entran al grafo.

## API pública

- `news_id_for(url)` — Id estable derivado de la URL: el mismo artículo es el mismo objeto, aunque llegue por dos búsquedas distintas. _(línea 49)_
- `ingest_item(session, item, entity_id=…, actor=…)` — Ingiere UN artículo normalizado (esquema de core/providers/news). _(línea 66)_
- `ingest_news_for(session, entity_id, query=…, limit=…, actor=…, provider_registry=…)` — Busca noticias de una entidad y las ingiere al grafo. _(línea 127)_
- `news_for_object(session, entity_id, limit=…)` — Noticias que informan sobre una entidad, de la más reciente a la más antigua (por fecha de PUBLICACIÓN, que es lo que le importa al … _(línea 176)_

**Internas** (empiezan con `_`): `_link_exists`

## Depende de

- [[core.providers.news.py]] — importa `news_registry`
- [[ontology.models.py]] — importa `LinkRecord`, `ObjectRecord`
- [[ontology.provenance.py]] — importa `EVIDENCE_REL`, `normalize_url`, `register_source`, `source_trust`
- [[ontology.service.py]] — importa `_parse_dt`, `_utcnow`, `apply_event`

## Lo usan

- [[ontology.api.py]] — lo importa
- [[ontology.timeline.py]] — lo importa

_Además lo importan 3 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_graph_api.py]]
- [[tests.test_ingest_news.py]]
- [[tests.test_ops_review_steps568.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-22 al 24 — PHASE 1 Live Investment Graph COMPLETA + velocidad + 3D temporal]]
