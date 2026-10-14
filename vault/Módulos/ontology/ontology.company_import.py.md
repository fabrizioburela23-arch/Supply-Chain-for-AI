---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/company_import.py"
lenguaje: "python"
lineas: 2022
aliases: ["ontology/company_import.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/company_import.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 2.022 líneas · `ontology/company_import.py`

## Para qué sirve

importador de fichas khipus.company/1 (docs/expansion/EXPANSION_5K.md, bloque E2).

## API pública

- clase `ImportProblem` — Mensaje en español (args[0]) + inglés (`en`) + código corto para la API. _(línea 56)_
- `policy(key=…)` — Valor de policy.import (gobernanza) o el de hoy si el artefacto no está en el release. _(línea 65)_
- `load_bundle(path)` — Archivo → {'records': [...], 'updates': [...], 'approve_categories': [...], 'batch': str|None}. `.jsonl`: una ficha por línea (líneas … _(línea 90)_
- `parse_bundle(text, name=…)` _(línea 99)_
- `validate_batch(records)` — [(dict, CompanyRecord)] válidos + [{record_id, index, errors}] inválidos. Puro. _(línea 126)_
- `id_index(view=…)` _(línea 210)_
- `resolve_ids(ids, name=…, view=…)` — Contrato E1.6: {'id','method','score','conflicts'} o None. DELEGA en core.entities.resolve_ids (el resolvedor único: detecta … _(línea 233)_
- `resolve_batch(valid, view=…)` — [(dict, model)] → {record_id: {'action', 'id', 'method', 'score', 'conflicts', 'reason'}}. Puro (lee el grafo vigente). Dos fichas del lote … _(línea 335)_
- `graph_key(view)` — Clave ESTABLE del grafo que vio el plan: fuente + versión + contenido del núcleo (el id de generación cambia con cada arranque del proceso; … _(línea 400)_
- `nearest_category(cat_id, sector, cats, c2s)` — Categoría EXISTENTE más parecida (misma sector + más palabras en común en el id; empate: la más usada en el catálogo, luego alfabético). … _(línea 414)_
- `company_props(model, rec, cid, cats, c2s, approved, pol, warnings)` — Propiedades del objeto Company (contrato E2): catálogo (cat/sector/country/ticker/mkt/role…) + ids + listings + hq/incorporation (ISO-2) + … _(línea 604)_
- `plan(records, updates=…, view=…, batch=…, approve_categories=…, pending=…, what_changes=…)` — PURO: no escribe nada. Devuelve el plan (qué se crea / fusiona / actualiza / omite y por qué; categorías por aprobar; vínculos por ruta; … _(línea 817)_
- `plan_sha(p)` — Huella de lo que SE APLICARÍA: ítems, actualizaciones, fuentes, categorías, política y generación del grafo (otro grafo = otra huella → 409 … _(línea 1079)_
- `kernel_what_changes(view, p)` — ρ, top-20 de cuellos de botella y a cuántas empresas golpea TSMC, ANTES (la vista Impact publicada) y DESPUÉS (los nodos + vínculos vivos … _(línea 1088)_
- `import_triples(item, pol=…)` — (tripletas, foco) de UN ítem del plan para `ontology.g_import`: la ficha `a kh:ImportRecord` y cada vínculo `a kh:ImportRelation`. Solo … _(línea 1179)_
- `gate_plan(items, session=…)` — G-IMPORT en bloque (sombra): un reporte para todos los ítems, registrado en la decisión en curso. _(línea 1226)_
- `events_of(p, run_id, revive_ids=…)` — El plan → la lista de eventos que apply_run escribe (en este orden): fuentes nuevas, empresas (crear/fusionar), actualizaciones, vínculos … _(línea 1254)_
- `new_run_id()` _(línea 1329)_
- `apply_run(session_scope, p, principal=…, confirm_db=…, expect=…, file_sha=…, run_id=…, log=…, view=…)` — Aplica el plan: UNA decisión `ontology.bulk_import`, UNA transacción, escritura por bloques (E2.8), puertas en sombra evaluadas en bloque, … _(línea 1377)_
- `list_runs(session, limit=…)` _(línea 1501)_
- `rollback_run(session, run_id, principal=…, confirm_db=…)` — Deshace una corrida con eventos NUEVOS (canal import_rb:&lt;run_id>) en UNA decisión `ontology.import_rollback`: vínculos creados → … _(línea 1538)_
- `consumed_pending_ids(session)` — Ids de import_pending_links que YA produjeron un LinkCreated (properties.from_pending) en una corrida import:\*. La tabla es append-only … _(línea 1626)_
- `pending_links(session, limit=…, include_consumed=…)` — Vínculos a la espera de su contraparte, SIN los que una corrida ya resolvió (consumed_pending_ids). _(línea 1643)_
- `render_summary(p, lang=…, limit=…)` — Markdown corto: conteos, categorías por aprobar, ¿qué cambia?, conflictos principales. _(línea 1657)_
- `adapt_lote_2026_10_14(path=…, categories=…)` — CSV del lote 1 → {'records': fichas nivel A, 'updates': países de las 937, 'approve_categories': las 56 propuestas (consolidadas), … _(línea 1855)_

**Internas** (empiezan con `_`): `_now`, `_canon`, `_sha`, `_IdIndex`, `_is_current`, `_suffix`, `_base_symbol`, `_ids_of`, `_catalog_cats`, `_best_evidence`, `_source_entry`, `_direction`, `_route_link`, `_resolve_counterparty`, `_counterparty_ids`, `_counterparty_dict`, `_link_spec`, `_holding_links`, `_fact`, `_text_pair`, `_record_sources`, `_short`, `_merge_nested`, `_events_estimate`, `_who`, `_rej_status`, `_confirm`, `_busy_import`, `_check_expect`, `_apply_locked`, `_run_uuid`, `_versions_after`, `_rollback_body`, `_read_csv`, `_domain_of`, `_primary_rule`, `_listing_kind`, `_listing`, `_strip_depositary_suffix`

## Depende de

- [[core.__init__.py]] — importa `builder`, `core.gates`, `focus`, `hot`, `report`, `signals`
- [[core.decisions.py]] — importa `decisions`
- [[core.entities.py]] — importa `entities`, `norm`
- [[core.governance.py]] — importa `governance`
- [[core.identity.py]] — importa `identity`
- [[core.import_normalize.py]] — importa `catalog_key_of`, `currency_of_mic`, `exchange_label`, `is_khipus_id`, `iso2_of`, `khipus_id_from`, `partial_date`, `pct` …
- [[core.instruments.py]] — importa `MINOR_UNITS`
- [[matrix.engine.py]] — importa `engine`
- [[ontology.bulk_import.py]] — importa `(dinámico: ontology.bulk_import)`, `write_events_fast`
- [[ontology.company_schema.py]] — importa `FORBIDDEN_KEYS`, `company_schema`
- [[ontology.db.py]] — importa `_get_engine`
- [[ontology.import_models.py]] — importa `ImportPendingLink`, `ImportRun`, `import_models`
- [[ontology.models.py]] — importa `Event`, `EventType`, `ObjectRecord`
- [[ontology.provenance.py]] — importa `SOURCE_TYPE`, `publisher_from_url`, `source_id_for`, `source_trust`
- [[ontology.reconcile.py]] — importa `LOCK_KEY`, `ReconcileError`, `_check_confirm`
- [[ontology.service.py]] — importa `GENESIS_SENTINEL`
- [[ontology.vocabulary.py]] — importa `categories`, `resolve_category`

## Lo usan

- [[ontology.api.py]] — lo importa
- [[scripts.import_companies.py]] — lo importa

_Además lo importan 6 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.gates_cases.py]]
- [[tests.test_import_adapter.py]]
- [[tests.test_import_governance.py]]
- [[tests.test_import_roundtrip.py]]
- [[tests.test_import_shapes.py]]
- [[tests.test_lotek_fixer.py]]
