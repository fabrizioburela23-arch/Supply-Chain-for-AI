---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/models.py"
lenguaje: "python"
lineas: 199
aliases: ["ontology/models.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/models.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 199 líneas · `ontology/models.py`

## Para qué sirve

esquema SQLAlchemy de la ontología.

## API pública

- clase `EventType` _(línea 29)_
- clase `Event` — Tabla append-only. NUNCA se hace UPDATE/DELETE sobre filas existentes — una corrección es un evento nuevo con su propio valid_from. _(línea 42)_
- clase `ObjectRecord` — Estado materializado ACTUAL de un objeto (empresa, tecnología, política…). `properties` acumula el último valor conocido de cada campo. _(línea 78)_
- clase `LinkRecord` — Vínculo materializado. `valid_to IS NULL` = vigente ahora mismo (según el conocimiento más reciente). Varias filas pueden existir para el … _(línea 91)_
- clase `ProposedAction` — Fase 3 — cola de aprobación. Un agente observa la ontología, detecta una señal y PROPONE una Acción del catálogo (ontology/actions.py); … _(línea 117)_
- clase `InsightSnapshot` — Track B — historial de /api/matrix/insights. _(línea 144)_
- clase `Alert` — Fase 4 — regla de alerta. rule = {entity, metric, op, value} para precio/NRS, o {region, event_type} para noticias por región. _(línea 179)_

## Depende de

- [[ontology.governance_models.py]] — importa `governance_models`
- [[ontology.history_models.py]] — importa `history_models`
- [[ontology.ledger_models.py]] — importa `ledger_models`

## Lo usan

- [[brokerage.models.py]] — lo importa
- [[core.ops_check.py]] — lo importa
- [[matrix.api.py]] — lo importa
- [[matrix.engine.py]] — lo importa
- [[mcp_server.models.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[ontology.actions.py]] — lo importa
- [[ontology.agents.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[ontology.bitemporal.py]] — lo importa
- [[ontology.bulk_import.py]] — lo importa
- [[ontology.checkpoints.py]] — lo importa
- [[ontology.db.py]] — lo importa
- [[ontology.governance_models.py]] — lo importa
- [[ontology.history_models.py]] — lo importa
- [[ontology.ingest_news.py]] — lo importa
- [[ontology.ledger_models.py]] — lo importa
- [[ontology.provenance.py]] — lo importa
- [[ontology.reconcile.py]] — lo importa
- [[ontology.service.py]] — lo importa
- [[ontology.timeline.py]] — lo importa
- [[research.api.py]] — lo importa
- [[research.models.py]] — lo importa
- [[scripts.migrate_v0_to_ontology.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `get_claim_evidence` → [[API herramientas MCP]]
- herramienta MCP `get_company` → [[API herramientas MCP]]
- herramienta MCP `get_ontology_object` → [[API herramientas MCP]]

_Además lo importan 67 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_agent_dudosos.py]]
- [[tests.test_ai_calls.py]]
- [[tests.test_bitemporal.py]]
- [[tests.test_bitemporal_review.py]]
- [[tests.test_brokerage.py]]
- [[tests.test_checkpoints.py]]
- [[tests.test_cierre_infra.py]]
- [[tests.test_committee_os_narr.py]]
- [[tests.test_gates_resulting_state.py]]
- [[tests.test_genui_ledger.py]]
- [[tests.test_governance.py]]
- [[tests.test_governance_activation.py]]
- [[tests.test_governance_flow.py]]
- [[tests.test_graph_api.py]]
- [[tests.test_hot_contract.py]]
- [[tests.test_hot_invalidation.py]]
- [[tests.test_hot_review_fixes.py]]
- [[tests.test_hot_views_parity.py]]
- [[tests.test_infra.py]]
- [[tests.test_ingest_news.py]]
- [[tests.test_ledger_anchor.py]]
- [[tests.test_ledger_callsites.py]]
- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_chain.py]]
- [[tests.test_ledger_core.py]]
- [[tests.test_ledger_guard.py]]
- [[tests.test_ledger_privacy.py]]
- [[tests.test_ledger_review_fixes.py]]
- [[tests.test_lotej_review_fixes.py]]
- [[tests.test_maptime_asof.py]]
- [[tests.test_matrix.py]]
- [[tests.test_mcp.py]]
- [[tests.test_ontology.py]]
- [[tests.test_ontology_actions.py]]
- [[tests.test_ontology_agents.py]]
- [[tests.test_ontology_alerts.py]]
- [[tests.test_ops_events_append_only.py]]
- [[tests.test_ops_graph_version.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_ops_link_status_event.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_ops_single_source.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_phase3.py]]
- [[tests.test_provenance.py]]
- [[tests.test_reconcile.py]]
- [[tests.test_repair_committee.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_repair_ontology.py]]
- [[tests.test_repair_ontology_review.py]]
- [[tests.test_repair_ops.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_research.py]]
- [[tests.test_retention_purge.py]]
- [[tests.test_review_batch_g.py]]
- [[tests.test_review_infra_c.py]]
- [[tests.test_rutas_acceso_decision.py]]
- [[tests.test_scale_hot_paging.py]]
- [[tests.test_scale_hot_rebuild.py]]
- [[tests.test_scale_search_d1d2.py]]
- [[tests.test_security.py]]
- [[tests.test_tensor_autolink.py]]
- [[tests.test_trading_agent_ledger.py]]
- [[tests.test_voice_agent_split.py]]
