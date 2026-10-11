---
tipo: "api"
capa: "Ontología y grafo temporal"
rutas: 33
tags: ["capa/ontologia", "tipo/api"]
---

# API ontology

> 33 rutas · definidas en [[ontology.api.py]] · prefijo `/api/ontology`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/ontology/actions` | `actions_list` | [[ontology.api.py]] | [[app.html]], 1 prueba |
| `POST` | `/api/ontology/actions/<action_type>` | `actions_execute` | [[ontology.api.py]] | [[engine.khipu_lang.js]], [[engine.temporal-graph.js]], 2 pruebas |
| `GET` | `/api/ontology/agents/brief` | `agents_brief` | [[ontology.api.py]] | 2 pruebas |
| `POST` | `/api/ontology/agents/cycle` | `agents_cycle` | [[ontology.api.py]] | [[engine.live.js]], 1 prueba |
| `POST` | `/api/ontology/agents/investigar` | `agents_investigar` | [[ontology.api.py]] | [[app.html]], 2 pruebas |
| `GET` | `/api/ontology/agents/proposals` | `agents_proposals_list` | [[ontology.api.py]] | [[app.html]], 2 pruebas |
| `POST` | `/api/ontology/agents/proposals/<proposal_id>/approve` | `agents_proposal_approve` | [[ontology.api.py]] | [[app.html]], 2 pruebas |
| `POST` | `/api/ontology/agents/proposals/<proposal_id>/reject` | `agents_proposal_reject` | [[ontology.api.py]] | [[app.html]], 1 prueba |
| `POST` | `/api/ontology/agents/run` | `agents_run` | [[ontology.api.py]] | [[app.html]], 2 pruebas |
| `GET` | `/api/ontology/alerts` | `alerts_list` | [[ontology.api.py]] | [[engine.khipu_lang.js]], 2 pruebas |
| `POST` | `/api/ontology/alerts` | `alerts_create` | [[ontology.api.py]] | [[engine.khipu_lang.js]], 2 pruebas |
| `DELETE` | `/api/ontology/alerts/<alert_id>` | `alerts_delete` | [[ontology.api.py]] | [[app.html]], 2 pruebas |
| `GET` | `/api/ontology/alerts/check` | `alerts_check` | [[ontology.api.py]] | [[app.html]], 2 pruebas |
| `POST` | `/api/ontology/bulk/import` | `bulk_import_route` | [[ontology.api.py]] | 1 prueba |
| `POST` | `/api/ontology/events` | `events_create` | [[ontology.api.py]] | 1 prueba |
| `GET` | `/api/ontology/events/<event_id>` | `event_detail` | [[ontology.api.py]] | 1 prueba |
| `GET` | `/api/ontology/feed` | `global_feed_route` | [[ontology.api.py]] | [[app.html]], [[engine.khipu_lang.js]], 1 prueba |
| `GET` | `/api/ontology/graph` | `graph` | [[ontology.api.py]] | — |
| `GET` | `/api/ontology/graph/diff` | `graph_diff` | [[ontology.api.py]] | [[engine.khipu_lang.js]] |
| `POST` | `/api/ontology/ingest/news` | `ingest_news` | [[ontology.api.py]] | [[app.html]], [[engine.temporal-graph.js]], 2 pruebas |
| `GET` | `/api/ontology/objects` | `objects_list` | [[ontology.api.py]] | [[engine.fincard.js]], 1 prueba |
| `GET` | `/api/ontology/objects/<object_id>` | `objects_get` | [[ontology.api.py]] | [[engine.fincard.js]], [[engine.temporal-graph.js]] |
| `GET` | `/api/ontology/objects/<object_id>/history` | `objects_history` | [[ontology.api.py]] | [[engine.fincard.js]] |
| `GET` | `/api/ontology/objects/<object_id>/links` | `objects_links` | [[ontology.api.py]] | [[engine.fincard.js]] |
| `GET` | `/api/ontology/objects/<object_id>/news` | `object_news` | [[ontology.api.py]] | [[engine.fincard.js]], 1 prueba |
| `GET` | `/api/ontology/objects/<object_id>/provenance` | `object_provenance` | [[ontology.api.py]] | [[engine.fincard.js]], 1 prueba |
| `GET` | `/api/ontology/objects/<object_id>/timeline` | `object_timeline` | [[ontology.api.py]] | [[app.html]], [[engine.fincard.js]], [[engine.temporal-graph.js]], 1 prueba |
| `POST` | `/api/ontology/reconcile/apply` | `reconcile_apply` | [[ontology.api.py]] | [[engine.reconcile.js]], 3 pruebas |
| `GET` | `/api/ontology/reconcile/plan` | `reconcile_plan` | [[ontology.api.py]] | [[engine.reconcile.js]], 3 pruebas |
| `POST` | `/api/ontology/reconcile/rollback` | `reconcile_rollback` | [[ontology.api.py]] | [[engine.reconcile.js]], 3 pruebas |
| `GET` | `/api/ontology/search` | `search_objects` | [[ontology.api.py]] | 1 prueba |
| `GET` | `/api/ontology/sources` | `sources_list` | [[ontology.api.py]] | 1 prueba |
| `GET` | `/api/ontology/status` | `status` | [[ontology.api.py]] | [[engine.temporal-graph.js]] |
