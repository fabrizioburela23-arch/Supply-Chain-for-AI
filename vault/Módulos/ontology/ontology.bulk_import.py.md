---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/bulk_import.py"
lenguaje: "python"
lineas: 173
aliases: ["ontology/bulk_import.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/bulk_import.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 173 líneas · `ontology/bulk_import.py`

## Para qué sirve

ingesta masiva idempotente y validada (Wikidata/GLEIF).

## API pública

- `validate_bulk_links(records, existing_ids, valid_rel_types=…)` — PURA (sin DB). Valida y normaliza registros de links importados. _(línea 32)_
- `import_links_bulk(session, records, provenance, batch_size=…, valid_from=…, actor=…)` — Aplica links importados de forma VALIDADA, IDEMPOTENTE y POR LOTES. _(línea 89)_

**Internas** (empiezan con `_`): `_idempotency_key`, `_flush_batch`

## Depende de

- [[matrix.engine.py]] — importa `REL_TYPES`
- [[ontology.models.py]] — importa `Event`, `LinkRecord`, `ObjectRecord`
- [[ontology.service.py]] — importa `apply_event`

## Lo usan

- [[core.decisions.py]] — lo importa
- [[ontology.api.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_bulk_import.py]]
- [[tests.test_repair_ontology_review.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-07-19 — Motor de matrices DISPERSAS + centralidad]]
