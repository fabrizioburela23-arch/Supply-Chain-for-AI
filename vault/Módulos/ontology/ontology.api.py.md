---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/api.py"
lenguaje: "python"
lineas: 1220
aliases: ["ontology/api.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/api.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 1.220 líneas · `ontology/api.py`

## Para qué sirve

API REST de la ontología: /api/ontology/\*

## API pública

- `status()` _(línea 151)_
- `gates_status()` — Puertas de validación (INFRA_OPERATIVA paso 10): modo (sombra), versión e ir_hash de las formas, reglas, cuántas veces avisó cada regla … _(línea 168)_
- `objects_list()` _(línea 187)_
- `objects_get(object_id)` _(línea 201)_
- `objects_links(object_id)` _(línea 211)_
- `objects_history(object_id)` _(línea 220)_
- `graph()` _(línea 228)_
- `graph_diff()` _(línea 240)_
- `actions_list()` — Panel '📋 Registro': timeline de Acciones ejecutadas, filtrable. _(línea 261)_
- `actions_execute(action_type)` — Catálogo de Acciones (Fase 2): CrearTesis, AnotarObjeto, MarcarRiesgo, ProponerVinculo, Confirmar/RechazarVinculo, RegistrarDecision, … _(línea 280)_
- `agents_run()` — Dispara una corrida de todos los agentes (o los que pida `only`). Pensado para un botón manual o un cron externo — ver ontology/agents.py … _(línea 316)_
- `agents_cycle()` — Ciclo EN VIVO (elección de Fabrizio 2026-07-10: automático + reversible): corre los 5 agentes, auto-aprueba las propuestas SEGURAS (anotar, … _(línea 380)_
- `bulk_import_route()` — Carga masiva AUDITADA: objects (solo tipos NO económicos del registro, p.ej. Seat) + links (vía ontology.bulk_import: validación de … _(línea 412)_
- `agents_investigar()` — Body: {query, actor, empresa_id?}. Responde al instante; el resultado aparece como ProposedAction en 🔔 Propuestas (y en GET de este estado). _(línea 503)_
- `agents_proposals_list()` _(línea 536)_
- `select_proposed(status, limit)` _(línea 549)_
- `agents_proposal_approve(proposal_id)` — Aprueba (con ediciones opcionales) → ejecuta la Acción real, auditada con actor='&lt;agente>, aprobado por &lt;humano>'. Reclamo atómico: ver … _(línea 629)_
- `agents_proposal_reject(proposal_id)` _(línea 664)_
- `agents_brief()` — Cronista: Brief Matinal — no requiere aprobación, es informativo. _(línea 679)_
- `alerts_list()` _(línea 698)_
- `select_alerts(owner)` _(línea 707)_
- `alerts_create()` — Body: {owner, rule:{entity,metric,op,value} o {region,event_type}, channel?}. _(línea 719)_
- `alerts_delete(alert_id)` _(línea 742)_
- `alerts_check()` — Evalúa las alertas activas (de `owner` si se pasa) y devuelve las que dispararon ahora — el cliente las convierte en notificaciones del … _(línea 760)_
- `search_objects()` — Búsqueda de entidades desde el SERVIDOR (Phase 1 · M5). _(línea 772)_
- `event_detail(event_id)` — Un evento concreto, con su procedencia resuelta (Phase 1 · M5). _(línea 824)_
- `object_timeline(object_id)` — Qué le ha pasado a esta entidad, en un solo hilo (Phase 1 · M5). Fusiona eventos del grafo y noticias, ordenado por cuándo fue cierto en el … _(línea 858)_
- `global_feed_route()` — Lo último que entró al grafo ENTERO (M6): noticias, relaciones nuevas o terminadas, tesis y acciones — sin la migración ni los precios. … _(línea 883)_
- `object_news(object_id)` — Noticias que informan sobre una entidad, ya en el grafo (Phase 1 · M4). Solo LEE: no dispara ingesta, para que abrir una ficha no provoque … _(línea 927)_
- `ingest_news()` — Ingiere noticias de una entidad AL GRAFO (Phase 1 · M4). Body: {entity_id, query?, limit?, actor?}. _(línea 948)_
- `sources_list()` — Documentos que respaldan hechos del grafo (Phase 1 · M1). Query: ?kind=primary&min_trust=2&limit=50. Ordenadas por confiabilidad. _(línea 994)_
- `object_provenance(object_id)` — De dónde salió lo que sabemos de este objeto: las fuentes que lo evidencian y los eventos que las citan (con fecha y confianza). _(línea 1024)_
- `events_create()` — Escritura de bajo nivel. En Fase 2 esto se envuelve con el catálogo de Acciones (validación por tipo, auditoría de actor humano). Por ahora … _(línea 1045)_
- `reconcile_plan()` — Dry-run: ?format=json (default) | md | html · ?lang=es|en · ?fresh=1. No escribe nada. _(línea 1108)_
- `reconcile_apply()` — Body: {actor, confirm_db, include: ['alias','duplicates',…], expect: {cat: n}}. Devuelve run_id. _(línea 1169)_
- `reconcile_rollback()` — Body: {actor, confirm_db, run_id}. Deshace con eventos nuevos. _(línea 1203)_

**Internas** (empiezan con `_`): `_unavailable`, `_body`, `_BadArg`, `_int_arg`, `_bad_arg`, `_ledger_unavailable`, `_principal`, `_require_db`, `_obj_to_dict`, `_mark_genesis`, `_link_to_dict`, `_event_to_dict`, `_action_event_to_dict`, `_proposal_to_dict`, `_cycle_bg`, `_try_start_cycle`, `_invest_bg`, `_claim_proposal`, `_cycle_may_auto_apply`, `_proposal_actor_and_id`, `_alert_to_dict`, `_recon_plan`, `_strict_operator`, `_strict_operator_required`, `_str_arg`

## Depende de

- [[core.__init__.py]] — importa `core.gates`
- [[core.decisions.py]] — importa `LedgerUnavailable`
- [[core.entities.py]] — importa `UMBRAL_BUSQUEDA`, `resolve`
- [[core.http.py]] — importa `rate_limit`
- [[core.identity.py]] — importa `identity`
- [[core.pin.py]] — importa `operator_strict`, `pin_error`, `require_operator`
- [[core.websearch.py]] — importa `_web_search_available`
- [[ontology.actions.py]] — importa `ActionError`, `execute_action`, `list_actions`
- [[ontology.agents.py]] — importa `AGENTS`, `AUTO_MIN_CONFIDENCE`, `SAFE_AUTO`, `auto_cycle`, `brief_matinal`, `check_alerts`, `run_agents`
- [[ontology.bulk_import.py]] — importa `import_links_bulk`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[ontology.ingest_news.py]] — importa `ingest_news_for`, `news_for_object`
- [[ontology.models.py]] — importa `Alert`, `Event`, `LinkRecord`, `ObjectRecord`, `ProposedAction`
- [[ontology.provenance.py]] — importa `SOURCE_TYPE`, `provenance_for_object`, `source_to_dict`
- [[ontology.reconcile.py]] — importa `reconcile`
- [[ontology.service.py]] — importa `OntologyError`, `_parse_dt`, `_utcnow`, `apply_event`, `as_of_graph`, `diff_graph`, `get_object`, `is_genesis` …
- [[ontology.timeline.py]] — importa `entity_timeline`, `global_feed`
- [[ontology.vocabulary.py]] — importa `is_economic`, `object_types`
- [[research.router.py]] — importa `dispatch_event`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 5 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/ontology/actions` | `actions_list` | [[app.html]], 1 prueba |
| `POST` | `/api/ontology/actions/<action_type>` | `actions_execute` | [[engine.khipu_lang.js]], [[engine.temporal-graph.js]], 4 pruebas |
| `GET` | `/api/ontology/agents/brief` | `agents_brief` | 2 pruebas |
| `POST` | `/api/ontology/agents/cycle` | `agents_cycle` | [[engine.live.js]], 2 pruebas |
| `POST` | `/api/ontology/agents/investigar` | `agents_investigar` | [[app.html]], 2 pruebas |
| `GET` | `/api/ontology/agents/proposals` | `agents_proposals_list` | [[app.html]], 2 pruebas |
| `POST` | `/api/ontology/agents/proposals/<proposal_id>/approve` | `agents_proposal_approve` | [[app.html]], 2 pruebas |
| `POST` | `/api/ontology/agents/proposals/<proposal_id>/reject` | `agents_proposal_reject` | [[app.html]], 1 prueba |
| `POST` | `/api/ontology/agents/run` | `agents_run` | [[app.html]], 2 pruebas |
| `GET` | `/api/ontology/alerts` | `alerts_list` | [[engine.khipu_lang.js]], 2 pruebas |
| `POST` | `/api/ontology/alerts` | `alerts_create` | [[engine.khipu_lang.js]], 2 pruebas |
| `DELETE` | `/api/ontology/alerts/<alert_id>` | `alerts_delete` | [[app.html]], 2 pruebas |
| `GET` | `/api/ontology/alerts/check` | `alerts_check` | [[app.html]], 2 pruebas |
| `POST` | `/api/ontology/bulk/import` | `bulk_import_route` | 1 prueba |
| `POST` | `/api/ontology/events` | `events_create` | 1 prueba |
| `GET` | `/api/ontology/events/<event_id>` | `event_detail` | 1 prueba |
| `GET` | `/api/ontology/feed` | `global_feed_route` | [[app.html]], [[engine.khipu_lang.js]], 1 prueba |
| `GET` | `/api/ontology/gates` | `gates_status` | — |
| `GET` | `/api/ontology/graph` | `graph` | — |
| `GET` | `/api/ontology/graph/diff` | `graph_diff` | [[engine.khipu_lang.js]] |
| `POST` | `/api/ontology/ingest/news` | `ingest_news` | [[app.html]], [[engine.temporal-graph.js]], 3 pruebas |
| `GET` | `/api/ontology/objects` | `objects_list` | [[engine.fincard.js]], 1 prueba |
| `GET` | `/api/ontology/objects/<object_id>` | `objects_get` | [[engine.fincard.js]], [[engine.temporal-graph.js]] |
| `GET` | `/api/ontology/objects/<object_id>/history` | `objects_history` | [[engine.fincard.js]] |
| `GET` | `/api/ontology/objects/<object_id>/links` | `objects_links` | [[engine.fincard.js]] |
| `GET` | `/api/ontology/objects/<object_id>/news` | `object_news` | [[engine.fincard.js]], 1 prueba |
| `GET` | `/api/ontology/objects/<object_id>/provenance` | `object_provenance` | [[engine.fincard.js]], 1 prueba |
| `GET` | `/api/ontology/objects/<object_id>/timeline` | `object_timeline` | [[app.html]], [[engine.fincard.js]], [[engine.temporal-graph.js]], 1 prueba |
| `POST` | `/api/ontology/reconcile/apply` | `reconcile_apply` | [[engine.reconcile.js]], 3 pruebas |
| `GET` | `/api/ontology/reconcile/plan` | `reconcile_plan` | [[engine.reconcile.js]], 3 pruebas |
| `POST` | `/api/ontology/reconcile/rollback` | `reconcile_rollback` | [[engine.reconcile.js]], 3 pruebas |
| `GET` | `/api/ontology/search` | `search_objects` | 1 prueba |
| `GET` | `/api/ontology/sources` | `sources_list` | 1 prueba |
| `GET` | `/api/ontology/status` | `status` | [[engine.temporal-graph.js]] |

Grupos: [[API ontology]]

## Variables de entorno que lee (solo nombres)

- [[ENV RESEARCH_AUTO_EVENTS]]

## Pruebas que lo cubren

- [[tests.test_graph_api.py]]
- [[tests.test_infra.py]]
- [[tests.test_ingest_news.py]]
- [[tests.test_ledger_core.py]]
- [[tests.test_ontology_agents.py]]
- [[tests.test_ontology_alerts.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_overnight2_sistema_shell.py]]
- [[tests.test_provenance.py]]
- [[tests.test_reconcile.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_repair_ontology_review.py]]
- [[tests.test_repair_review2.py]]
