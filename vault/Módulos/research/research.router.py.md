---
tipo: "modulo"
capa: "Investigación"
ruta: "research/router.py"
lenguaje: "python"
lineas: 133
aliases: ["research/router.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/router.py

> Módulo · capa [[Capa Investigación]] · 133 líneas · `research/router.py`

## Para qué sirve

evento → relevancia → agentes (Phase 2 event-driven).

## API pública

- `agents_for(event_type)` _(línea 25)_
- `relevant_entities(event, limits=…)` — Devuelve lista ordenada [{id, label, distance, via}] acotada por límites. _(línea 40)_
- `event_key(event)` _(línea 93)_
- `dispatch_event(session, event, actor=…, execute=…, limits=…, now=…)` — Clasifica el evento, calcula relevancia y crea jobs QUICK para las entidades más relevantes con los agentes suscritos. Idempotente 24 h. _(línea 99)_

**Internas** (empiezan con `_`): `_country_nodes`

## Depende de

- [[core.entities.py]] — importa `UMBRAL_BUSQUEDA`, `_SNAPSHOT`, `get_index`, `resolve`
- [[research.agents.__init__.py]] — importa `AGENTS`
- [[research.models.py]] — importa `ResearchJob`
- [[research.runner.py]] — importa `create_job`, `execute_job_async`

## Lo usan

- [[ontology.api.py]] — lo importa
- [[research.api.py]] — lo importa
- [[research.auto_events.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_research.py]]
