---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/bulk_import.py"
lenguaje: "python"
lineas: 340
aliases: ["ontology/bulk_import.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/bulk_import.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 340 líneas · `ontology/bulk_import.py`

## Para qué sirve

ingesta masiva idempotente y validada (Wikidata/GLEIF).

## API pública

- `validate_bulk_links(records, existing_ids, valid_rel_types=…)` — PURA (sin DB). Valida y normaliza registros de links importados. _(línea 32)_
- `evidence_ids(rec, props=…)` — Fuentes (`Source`, ontology/provenance.py) que el registro CITA: `evidenced_by` (lista o texto) y/o `source_id`, en el registro o en sus … _(línea 84)_
- `import_links_bulk(session, records, provenance, batch_size=…, valid_from=…, actor=…)` — Aplica links importados de forma VALIDADA, IDEMPOTENTE y POR LOTES. _(línea 111)_

**Internas** (empiezan con `_`): `_idempotency_key`, `_apply_accepted`, `_chunks`, `_bulk_context`, `_trust_num`, `_mark_primary_source`, `_gate_bulk`, `_flush_batch`

## Depende de

- [[core.__init__.py]] — importa `core.gates`, `focus`, `report`
- [[matrix.engine.py]] — importa `REL_TYPES`
- [[ontology.models.py]] — importa `Event`, `LinkRecord`, `ObjectRecord`
- [[ontology.service.py]] — importa `apply_event`

## Lo usan

- [[core.decisions.py]] — lo importa
- [[core.replay.py]] — lo importa
- [[ontology.api.py]] — lo importa

_Además lo importan 6 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_bulk_import.py]]
- [[tests.test_cierre_infra.py]]
- [[tests.test_gates_resulting_state.py]]
- [[tests.test_repair_ontology_review.py]]
- [[tests.test_scale_hot_rebuild.py]]
- [[tests.test_scale_search_d1d2.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-07-19 — Motor de matrices DISPERSAS + centralidad]]
