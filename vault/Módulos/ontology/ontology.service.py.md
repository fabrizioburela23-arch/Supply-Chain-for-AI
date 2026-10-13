---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/service.py"
lenguaje: "python"
lineas: 622
aliases: ["ontology/service.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/service.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 622 líneas · `ontology/service.py`

## Para qué sirve

lógica de negocio de la ontología.

## API pública

- clase `OntologyError` _(línea 27)_
- `is_genesis(dt)` — ¿`dt` es la fecha centinela (2000-01-01)? Acepta datetime (con o sin zona), date, texto ISO o None. Solo mira el día: el centinela se … _(línea 45)_
- `apply_event(session, event_type, payload, valid_from, source, actor, object_id=…, target_id=…, valid_to=…, source_id=…, confidence=…)` — Inserta el evento (inmutable) y actualiza objects/links (materializado). Devuelve el Event insertado. Lanza OntologyError si el evento es … _(línea 100)_
- `get_object(session, object_id)` _(línea 458)_
- `list_objects(session, type_=…, q=…, limit=…, offset=…)` _(línea 462)_
- `func_lower_like(col, pattern)` _(línea 473)_
- `object_links(session, object_id, direction=…)` — Vínculos VIGENTES ahora (valid_to IS NULL) para un objeto. _(línea 478)_
- `object_history(session, object_id)` — Todos los eventos donde el objeto participó (como object_id o target_id), ordenados por valid_from. Es la 'línea de tiempo' del objeto. _(línea 492)_
- `as_of_graph(session, as_of_dt=…)` — Grafo (nodos + aristas) vigente en `as_of_dt` (default: ahora). _(línea 589)_
- `diff_graph(session, from_dt, to_dt)` — Qué vínculos aparecieron/desaparecieron entre dos fechas de validez. _(línea 606)_

**Internas** (empiezan con `_`): `_utcnow`, `_parse_dt`, `_vigilar_vocabulario`, `_same_weight`, `_dedup_link_payload`, `_creation_event_for`, `_wkey`, `_pair_history`, `_killed`, `_promotion_choice`, `_promote_dedup`, `_replay_promotions`, `_uuid_str`, `_materialize`, `_apply_link_status`, `_links_active_at`

## Depende de

- [[core.__init__.py]] — importa `signals`
- [[ontology.models.py]] — importa `Event`, `EventType`, `LinkRecord`, `ObjectRecord`
- [[ontology.vocabulary.py]] — importa `vocabulary`

## Lo usan

- [[matrix.api.py]] — lo importa
- [[matrix.engine.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[ontology.actions.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[ontology.bulk_import.py]] — lo importa
- [[ontology.ingest_news.py]] — lo importa
- [[ontology.provenance.py]] — lo importa
- [[ontology.reconcile.py]] — lo importa
- [[ontology.timeline.py]] — lo importa
- [[scripts.migrate_v0_to_ontology.py]] — lo importa
- herramienta MCP `get_ontology_object` → [[API herramientas MCP]]

_Además lo importan 24 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_agent_dudosos.py]]
- [[tests.test_graph_api.py]]
- [[tests.test_hot_contract.py]]
- [[tests.test_hot_invalidation.py]]
- [[tests.test_hot_review_fixes.py]]
- [[tests.test_hot_views_parity.py]]
- [[tests.test_infra.py]]
- [[tests.test_ingest_news.py]]
- [[tests.test_matrix.py]]
- [[tests.test_ontology.py]]
- [[tests.test_ontology_actions.py]]
- [[tests.test_ontology_agents.py]]
- [[tests.test_ontology_alerts.py]]
- [[tests.test_ops_events_append_only.py]]
- [[tests.test_ops_graph_version.py]]
- [[tests.test_ops_link_status_event.py]]
- [[tests.test_provenance.py]]
- [[tests.test_reconcile.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_repair_ontology.py]]
- [[tests.test_repair_ontology_review.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_tensor_autolink.py]]
- [[tests.test_vocabulary.py]]
