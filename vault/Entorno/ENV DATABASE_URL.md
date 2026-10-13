---
tipo: "variable"
capa: "Infraestructura"
nombre: "DATABASE_URL"
documentada: true
tags: ["capa/infraestructura", "tipo/variable"]
---

# DATABASE_URL

> Variable de entorno · se configura en Railway (Variables). Aquí solo el **nombre**, nunca el valor.

## La leen

- [[core.http.py]] _(en una lista de nombres, p. ej. para tapar secretos en logs)_
- [[ontology.db.py]]
- [[scripts.audit_graph.py]]
- [[scripts.build_graph_review.py]]
- [[scripts.migrate_v0_to_ontology.py]]
- [[scripts.reconcile_v0_to_ontology.py]]

## Pruebas que la fijan o nombran

- [[tests.test_agent_dudosos.py]]
- [[tests.test_ai_calls.py]]
- [[tests.test_ai_usage.py]]
- [[tests.test_ai_usage_cache.py]]
- [[tests.test_block0_ci.py]]
- [[tests.test_brokerage.py]]
- [[tests.test_committee_os_narr.py]]
- [[tests.test_gates_resulting_state.py]]
- [[tests.test_governance.py]]
- [[tests.test_governance_activation.py]]
- [[tests.test_graph_api.py]]
- [[tests.test_hot_contract.py]]
- [[tests.test_hot_invalidation.py]]
- [[tests.test_hot_review_fixes.py]]
- [[tests.test_hot_views_parity.py]]
- [[tests.test_infra.py]]
- [[tests.test_ingest_news.py]]
- [[tests.test_instruments.py]]
- [[tests.test_ledger_anchor.py]]
- [[tests.test_ledger_callsites.py]]
- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_chain.py]]
- [[tests.test_ledger_core.py]]
- [[tests.test_ledger_privacy.py]]
- [[tests.test_ledger_review_fixes.py]]
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
- [[tests.test_portfolio_persist.py]]
- [[tests.test_portfolio_reports.py]]
- [[tests.test_prices_eod.py]]
- [[tests.test_provenance.py]]
- [[tests.test_reconcile.py]]
- [[tests.test_repair_committee.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_repair_ontology.py]]
- [[tests.test_repair_ontology_review.py]]
- [[tests.test_repair_ops.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_research.py]]
- [[tests.test_review_infra_c.py]]
- [[tests.test_review_lists.py]]
- [[tests.test_risk_on_history.py]]
- [[tests.test_security.py]]
- [[tests.test_server_smoke.py]]
- [[tests.test_tensor_autolink.py]]
- [[tests.test_trading_agent_ledger.py]]

## ¿Está documentada en CLAUDE.md?

Sí — en la lista **Variables de entorno** de [[Doc CLAUDE]].

## Mencionada en sesiones

- [[Sesión 2026-09-22 al 24 — PHASE 1 Live Investment Graph COMPLETA + velocidad + 3D temporal]]
- [[Sesión 2026-09-21 — Limpieza estructural - Track A Fase 2 + Track B completos]]
- [[Sesión 2026-07-07 — Etapa 3 — Motor de matrices + hiperaristas - NÚCLEO COMPLETO]]
- [[Sesión 2026-10-03 — VISIÓN PRÓXIMA ETAPA (pedido, NO es parte de Phase 3)]]
