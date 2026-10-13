---
tipo: "modulo"
capa: "Investigación"
ruta: "research/router.py"
lenguaje: "python"
lineas: 141
aliases: ["research/router.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/router.py

> Módulo · capa [[Capa Investigación]] · 141 líneas · `research/router.py`

## Para qué sirve

evento → relevancia → agentes (Phase 2 event-driven).

## API pública

- `agents_for(event_type)` _(línea 25)_
- `graph_version()` — La generación del grafo que usa el enrutador de eventos (tests/test_ops_single_source.py). _(línea 47)_
- `relevant_entities(event, limits=…)` — Devuelve lista ordenada [{id, label, distance, via}] acotada por límites. _(línea 53)_
- `event_key(event)` _(línea 101)_
- `dispatch_event(session, event, actor=…, execute=…, limits=…, now=…)` — Clasifica el evento, calcula relevancia y crea jobs QUICK para las entidades más relevantes con los agentes suscritos. Idempotente 24 h. _(línea 107)_

**Internas** (empiezan con `_`): `_country_nodes`, `_links`

## Depende de

- [[core.__init__.py]] — importa `hot`
- [[core.entities.py]] — importa `UMBRAL_BUSQUEDA`, `get_index`, `resolve`
- [[research.agents.__init__.py]] — importa `AGENTS`
- [[research.models.py]] — importa `ResearchJob`
- [[research.runner.py]] — importa `create_job`, `execute_job_async`

## Lo usan

- [[ontology.api.py]] — lo importa
- [[research.api.py]] — lo importa
- [[research.auto_events.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_ops_single_source.py]]
- [[tests.test_research.py]]
