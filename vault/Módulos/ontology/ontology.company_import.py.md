---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/company_import.py"
lenguaje: "python"
lineas: 2699
aliases: ["ontology/company_import.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/company_import.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 2.699 líneas · `ontology/company_import.py`

## Para qué sirve

importador de fichas khipus.company/1 (docs/expansion/EXPANSION_5K.md, bloque E2).

## API pública

- clase `ImportProblem` — Mensaje en español (args[0]) + inglés (`en`) + código corto para la API. _(línea 62)_
- `policy(key=…)` — Valor de policy.import (gobernanza) o el de hoy si el artefacto no está en el release. _(línea 71)_
- `load_bundle(path)` — Archivo → {'records': [...], 'updates': [...], 'approve_categories': [...], 'batch': str|None}. `.jsonl`: una ficha por línea (líneas … _(línea 96)_
- `parse_bundle(text, name=…)` _(línea 113)_
- `validate_batch(records)` — [(dict, CompanyRecord)] válidos + [{record_id, index, errors}] inválidos. Puro. _(línea 140)_
- `sanitize_batch(records)` — Saneador de FORMATO (core/import_normalize.sanitize_record) sobre un lote → (fichas, registros, resumen). `registros` = {record_id (o … _(línea 170)_
- `id_index(view=…)` _(línea 247)_
- `resolve_ids(ids, name=…, view=…)` — Contrato E1.6: {'id','method','score','conflicts'} o None. DELEGA en core.entities.resolve_ids (el resolvedor único: detecta … _(línea 270)_
- `resolve_batch(valid, view=…)` — [(dict, model)] → {record_id: {'action', 'id', 'method', 'score', 'conflicts', 'reason'}}. Puro (lee el grafo vigente). Dos fichas del lote … _(línea 430)_
- `graph_key(view)` — Clave ESTABLE del grafo que vio el plan: fuente + versión + contenido del núcleo (el id de generación cambia con cada arranque del proceso; … _(línea 512)_
- `nearest_category(cat_id, sector, cats, c2s)` — Categoría EXISTENTE más parecida (misma sector + más palabras en común en el id; empate: la más usada en el catálogo, luego alfabético). … _(línea 526)_
- `company_props(model, rec, cid, cats, c2s, approved, pol, warnings)` — Propiedades del objeto Company (contrato E2): catálogo (cat/sector/country/ticker/mkt/role…) + ids + listings + hq/incorporation (ISO-2) + … _(línea 936)_
- `plan(records, updates=…, view=…, batch=…, approve_categories=…, pending=…, what_changes=…, sanitize=…)` — PURO: no escribe nada. Devuelve el plan (qué se crea / fusiona / actualiza / omite y por qué; categorías por aprobar; vínculos por ruta; … _(línea 1175)_
- `plan_sha(p)` — Huella de lo que SE APLICARÍA: ítems, actualizaciones, fuentes, categorías, política y generación del grafo (otro grafo = otra huella → 409 … _(línea 1473)_
- `kernel_what_changes(view, p)` — ρ, top-20 de cuellos de botella y a cuántas empresas golpea TSMC, ANTES (la vista Impact publicada) y DESPUÉS (los nodos + vínculos vivos … _(línea 1492)_
- `import_triples(item, pol=…)` — (tripletas, foco) de UN ítem del plan para `ontology.g_import`: la ficha `a kh:ImportRecord` y cada vínculo `a kh:ImportRelation`. Solo … _(línea 1583)_
- `gate_plan(items, session=…)` — G-IMPORT en bloque (sombra): un reporte para todos los ítems, registrado en la decisión en curso. _(línea 1632)_
- `events_of(p, run_id, revive_ids=…)` — El plan → la lista de eventos que apply_run escribe (en este orden): fuentes nuevas, empresas (crear/fusionar), actualizaciones, vínculos … _(línea 1660)_
- `new_run_id()` _(línea 1738)_
- `apply_run(session_scope, p, principal=…, confirm_db=…, expect=…, file_sha=…, run_id=…, log=…, view=…)` — Aplica el plan: UNA decisión `ontology.bulk_import`, UNA transacción, escritura por bloques (E2.8), puertas en sombra evaluadas en bloque, … _(línea 1786)_
- `list_runs(session, limit=…)` _(línea 1910)_
- `rollback_run(session, run_id, principal=…, confirm_db=…)` — Deshace una corrida con eventos NUEVOS (canal import_rb:&lt;run_id>) en UNA decisión `ontology.import_rollback`: vínculos creados → … _(línea 1947)_
- `consumed_pending_ids(session)` — Ids de import_pending_links que YA produjeron un LinkCreated (properties.from_pending) en una corrida import:\*. La tabla es append-only … _(línea 2035)_
- `pending_links(session, limit=…, include_consumed=…)` — Vínculos a la espera de su contraparte, SIN los que una corrida ya resolvió (consumed_pending_ids) y SIN los de una corrida DESHECHA … _(línea 2052)_
- `render_summary(p, lang=…, limit=…)` — Markdown corto: conteos, categorías por aprobar, ¿qué cambia?, conflictos principales. _(línea 2082)_
- `adapt_lote_2026_10_14(path=…, categories=…)` — CSV del lote 1 → {'records': fichas nivel A, 'updates': países de las 937, 'approve_categories': las 56 propuestas (consolidadas), … _(línea 2284)_
- `complete_record_ids(d=…)` — Los record_id de las fichas COMPLETAS (una por línea; vacías y '#' se ignoran), en el orden del archivo. _(línea 2472)_
- `build_lote_2026_10_15(d=…)` — fichas_completas.jsonl.gz + completas_record_ids.txt → {'bundle', 'log', 'kept', 'missing'}. Solo entran las fichas cuyo record_id está en … _(línea 2478)_
- `lote2_texts(built)` — (texto JSON del paquete, texto JSON del registro): la forma CANÓNICA que se escribe y que --check compara (se compara el texto, no los … _(línea 2504)_
- `render_lote2_md(p, built, d=…)` — El plan del lote 2026-10-15 en español simple. Determinista (sin horas ni milisegundos). _(línea 2563)_

**Internas** (empiezan con `_`): `_now`, `_canon`, `_sha`, `_IdIndex`, `_is_current`, `_suffix`, `_base_symbol`, `_ids_of`, `_identity_contradiction`, `_explicit_counterparty_ids`, `_hint_in_graph`, `_catalog_cats`, `_best_evidence`, `_source_entry`, `_merge_source`, `_direction`, `_route_link`, `_route_resolved_pending`, `_proposed_props`, `_batch_index`, `_resolve_counterparty`, `_counterparty_ids`, `_counterparty_dict`, `_owns_default_criticality`, `_owns_pct_from_corporate`, `_link_spec`, `_holding_link_without_pct`, `_holding_links`, `_fact`, `_text_pair`, `_fiscal_year_label_start`, `_record_sources`, `_short`, `_merge_nested`, `_events_estimate`, `_nnz`, `_who`, `_rej_status`, `_confirm`, `_busy_import`, `_check_expect`, `_apply_locked`, `_run_uuid`, `_versions_after`, `_rollback_body`, `_default_weight_text`, `_read_csv`, `_domain_of`, `_primary_rule`, `_listing_kind`, `_listing`, `_strip_depositary_suffix`, `_read_lines_gz`, `_n`

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

- [[core.import_normalize.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[scripts.import_companies.py]] — lo importa

_Además lo importan 15 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.gates_cases.py]]
- [[tests.test_catalog_api_pg.py]]
- [[tests.test_import_adapter.py]]
- [[tests.test_import_governance.py]]
- [[tests.test_import_lote2.py]]
- [[tests.test_import_lote2_e2e.py]]
- [[tests.test_import_panel.py]]
- [[tests.test_import_panel_browser.py]]
- [[tests.test_import_panel_static.py]]
- [[tests.test_import_roundtrip.py]]
- [[tests.test_import_sanitize_schema.py]]
- [[tests.test_import_shapes.py]]
- [[tests.test_live_universe_db.py]]
- [[tests.test_lotek_fixer.py]]
- [[tests.test_lotel_fixer.py]]
