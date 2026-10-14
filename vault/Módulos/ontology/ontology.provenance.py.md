---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/provenance.py"
lenguaje: "python"
lineas: 285
aliases: ["ontology/provenance.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/provenance.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 285 líneas · `ontology/provenance.py`

## Para qué sirve

Phase 1 · M1: procedencia de primera clase.

## API pública

- `normalize_url(url)` — Normaliza para deduplicar: esquema/host en minúsculas, sin parámetros de rastreo, sin fragmento, sin barra final. Devuelve None si no es … _(línea 54)_
- `source_id_for(url)` — Id estable y derivado de la URL — mismo documento ⇒ mismo id, siempre. _(línea 77)_
- `publisher_from_url(url)` — Dominio como publicador de respaldo cuando la fuente no lo declara. _(línea 85)_
- `source_kinds()` — Los tipos de fuente del vocabulario (con su `trust`). Si el vocabulario no se puede leer, se degrada a un mínimo razonable en vez de … _(línea 94)_
- `source_trust(kind)` — 0-3. Un `kind` desconocido vale 0: preferimos subestimar una fuente antes que darle confianza que nadie declaró. _(línea 107)_
- `guess_kind(url, declared=…)` — Si quien registra la fuente declara un `kind` válido, manda. Si no, se infiere de la URL de forma conservadora: ante la duda, 'aggregator' … _(línea 139)_
- `register_source(session, url, kind=…, title=…, publisher=…, published_at=…, retrieved_at=…, extractor=…, raw_ref=…, actor=…)` — Registra (o reutiliza) la entidad `Source` de una URL. Idempotente: si el documento ya existe, NO lo duplica ni lo sobreescribe — solo … _(línea 160)_
- `link_evidence(session, object_id, source_id, actor=…, quote=…)` — Enlaza un objeto con la fuente que lo evidencia (`evidenced_by`). _(línea 211)_
- `source_to_dict(obj)` _(línea 223)_
- `provenance_for_object(session, object_id, limit=…)` — De dónde salió lo que sabemos de este objeto. _(línea 236)_

**Internas** (empiezan con `_`): `_utcnow`

## Depende de

- [[ontology.models.py]] — importa `Event`, `LinkRecord`, `ObjectRecord`
- [[ontology.service.py]] — importa `apply_event`
- [[ontology.vocabulary.py]] — importa `source_kinds`

## Lo usan

- [[core.providers.news.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[ontology.actions.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[ontology.ingest_news.py]] — lo importa
- [[ontology.timeline.py]] — lo importa
- [[research.api.py]] — lo importa
- [[research.context.py]] — lo importa
- [[research.runner.py]] — lo importa
- herramienta MCP `get_claim_evidence` → [[API herramientas MCP]]
- herramienta MCP `get_ontology_object` → [[API herramientas MCP]]

_Además lo importan 3 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_graph_api.py]]
- [[tests.test_provenance.py]]
- [[tests.test_scale_search_d1d2.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-22 al 24 — PHASE 1 Live Investment Graph COMPLETA + velocidad + 3D temporal]]
