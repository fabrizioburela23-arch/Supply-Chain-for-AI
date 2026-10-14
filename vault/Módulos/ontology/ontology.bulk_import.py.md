---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/bulk_import.py"
lenguaje: "python"
lineas: 658
aliases: ["ontology/bulk_import.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/bulk_import.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 658 líneas · `ontology/bulk_import.py`

## Para qué sirve

ingesta masiva idempotente y validada (Wikidata/GLEIF).

## API pública

- `validate_bulk_links(records, existing_ids, valid_rel_types=…)` — PURA (sin DB). Valida y normaliza registros de links importados. _(línea 32)_
- `evidence_ids(rec, props=…)` — Fuentes (`Source`, ontology/provenance.py) que el registro CITA: `evidenced_by` (lista o texto) y/o `source_id`, en el registro o en sus … _(línea 90)_
- `import_links_bulk(session, records, provenance, batch_size=…, valid_from=…, actor=…)` — Aplica links importados de forma VALIDADA, IDEMPOTENTE y POR LOTES. _(línea 117)_
- `write_events_fast(session, events, source, actor, chunk=…, gate=…)` — Escribe `events` en bloques. Cada evento: {event_type, object_id, target_id, payload, valid_from (OBLIGATORIA), valid_to, source_id, … _(línea 424)_
- `gate_links_block(session, link_rows, confs=…)` — G-BULK para vínculos ya materializados en el bloque (cada uno con su valid_from): reporte único, registrado en la decisión en curso; en … _(línea 617)_

**Internas** (empiezan con `_`): `_idempotency_key`, `_apply_accepted`, `_chunks`, `_bulk_context`, `_trust_num`, `_mark_primary_source`, `_gate_bulk`, `_flush_batch`, `_json`, `_EvRef`, `_preload_objects`, `_preload_live_links`, `_dedup_twin`, `_write_block`

## Depende de

- [[core.__init__.py]] — importa `core.gates`, `focus`, `report`, `signals`
- [[core.decisions.py]] — importa `decisions`
- [[matrix.engine.py]] — importa `REL_TYPES`
- [[ontology.models.py]] — importa `Event`, `EventType`, `LinkRecord`, `ObjectRecord`
- [[ontology.service.py]] — importa `OntologyError`, `VALID_EVENT_TYPES`, `_parse_dt`, `_promote_dedup`, `_release_hash`, `_same_weight`, `_vigilar_vocabulario`, `apply_event`

## Lo usan

- [[core.decisions.py]] — lo importa
- [[core.replay.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[ontology.company_import.py]] — lo importa

_Además lo importan 9 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_bulk_import.py]]
- [[tests.test_cierre_infra.py]]
- [[tests.test_gates_resulting_state.py]]
- [[tests.test_import_fast_path.py]]
- [[tests.test_import_governance.py]]
- [[tests.test_import_roundtrip.py]]
- [[tests.test_repair_ontology_review.py]]
- [[tests.test_scale_hot_rebuild.py]]
- [[tests.test_scale_search_d1d2.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-14 (c) — LOTE K - IMPORTADOR DE EMPRESAS, PAÍSES ISO-2, CATEGORÍAS, CHAT]]
- [[Sesión 2026-07-19 — Motor de matrices DISPERSAS + centralidad]]
