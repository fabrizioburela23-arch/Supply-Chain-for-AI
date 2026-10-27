---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "data/grafo_v0.json"
lenguaje: "json"
lineas: 46123
aliases: ["data/grafo_v0.json"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# data/grafo_v0.json

> Datos · capa [[Capa Datos del catálogo]] · 46.123 líneas · `data/grafo_v0.json`

## Para qué sirve

Generado desde nodes/\*.js vía nodes/merge_graph.js (misma implementación que el navegador)

## Qué datos contiene

| Clave | Tipo | Tamaño / valor |
|---|---|---|
| `exported_at` | fecha | `2026-10-27T23:42:02.929Z` |
| `counts` | objeto | 8 |
| `nodes` | lista | 937 |
| `links` | lista | 2.510 |
| `node_id_alias` | objeto | 93 |
| `legal_names` | objeto | 159 |
| `voice_aliases` | objeto | 210 |
| `resolve_stopwords` | lista | 14 |
| `categories` | objeto | 163 |
| `sectors9` | objeto | 13 |
| `cat_to_sector` | objeto | 163 |
| `preipo_intel` | objeto | 14 |
| `temporal_facts` | lista | 105 |
| `ontology` | objeto | 4 |

## Depende de

_Nada interno._

## Lo usan

- [[ontology.reconcile.py]] — lo nombra por su ruta
- [[scripts.audit_graph.py]] — lo nombra por su ruta
- [[scripts.build_categories.py]] — lo nombra por su ruta
- [[scripts.build_country_review.py]] — lo nombra por su ruta
- [[scripts.build_graph_review.py]] — lo nombra por su ruta
- [[scripts.build_instrument_review.py]] — lo nombra por su ruta
- [[scripts.ingest_multicapa.py]] — lo nombra por su ruta
- [[scripts.links_to_ficha.py]] — lo nombra por su ruta
- [[scripts.migrate_v0_to_ontology.py]] — lo nombra por su ruta
- [[scripts.research_batch.py]] — lo nombra por su ruta

## Pruebas que lo cubren

- [[tests.test_alias_voz_paridad.py]]
- [[tests.test_catalog_api.py]]
- [[tests.test_catalog_fix_categories.py]]
- [[tests.test_catalog_fix_symbols.py]]
- [[tests.test_cleanup_nrs_parity.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_countries.py]]
- [[tests.test_docs_facts.py]]
- [[tests.test_entities.py]]
- [[tests.test_genui_browser.py]]
- [[tests.test_genui_rivals.py]]
- [[tests.test_genui_validate.py]]
- [[tests.test_graph_audit.py]]
- [[tests.test_import_normalize.py]]
- [[tests.test_instruments.py]]
- [[tests.test_kernel_reference_figures.py]]
- [[tests.test_khipu_chat.py]]
- [[tests.test_khipus_os_chat.py]]
- [[tests.test_live_universe.py]]
- [[tests.test_maptime_asof.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_ontology.py]]
- [[tests.test_ops_single_source.py]]
- [[tests.test_prices_eod.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_scenario_pnl_browser.py]]
- [[tests.test_server_smoke.py]]
- [[tests.test_voice_tour.py]]
- [[tests.test_world.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (ff) — ONTOLOGÍA NIVEL 2 - TENSORES + AUTO-CONEXIÓN (sw v241)]]
- [[Sesión 2026-10-04 (h) — MISIÓN DE REPARACIÓN P0 INVESTIGACIÓN (R1-R6, sw v201)]]
- [[Sesión 2026-07-06 — Etapa 2 — Datos limpios - COMPLETA (5 batches publicados)]]
- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
