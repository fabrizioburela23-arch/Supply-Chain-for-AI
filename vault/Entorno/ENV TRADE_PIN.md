---
tipo: "variable"
capa: "Infraestructura"
nombre: "TRADE_PIN"
documentada: true
tags: ["capa/infraestructura", "tipo/variable"]
---

# TRADE_PIN

> Variable de entorno · se configura en Railway (Variables). Aquí solo el **nombre**, nunca el valor.

## La leen

- [[brokerage.service.py]]
- [[core.http.py]] _(en una lista de nombres, p. ej. para tapar secretos en logs)_
- [[core.pin.py]]
- [[mcp_server.api.py]]
- [[mcp_server.auth.py]]
- [[scripts.import_companies.py]]
- [[server.py]]

## Pruebas que la fijan o nombran

- [[tests.test_ai_usage.py]]
- [[tests.test_brokerage.py]]
- [[tests.test_cierre_infra.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_gates_resulting_state.py]]
- [[tests.test_governance.py]]
- [[tests.test_governance_activation.py]]
- [[tests.test_governance_flow.py]]
- [[tests.test_import_lote2_e2e.py]]
- [[tests.test_import_panel.py]]
- [[tests.test_import_roundtrip.py]]
- [[tests.test_infra.py]]
- [[tests.test_ledger_anchor.py]]
- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_core.py]]
- [[tests.test_ledger_privacy.py]]
- [[tests.test_mcp.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_overnight_voice_server.py]]
- [[tests.test_phase3.py]]
- [[tests.test_prices_eod.py]]
- [[tests.test_reconcile.py]]
- [[tests.test_repair_ontology_review.py]]
- [[tests.test_repair_ops.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_review_batch_g.py]]
- [[tests.test_rutas_acceso_decision.py]]
- [[tests.test_security.py]]
- [[tests.test_trading_agent_ledger.py]]
- [[tests.test_voice_agent_split.py]]

## ¿Está documentada en CLAUDE.md?

Sí — en la lista **Variables de entorno** de [[Doc CLAUDE]].

## Mencionada en sesiones

- [[Sesión 2026-10-13 (b) — INFRAESTRUCTURA OPERATIVA, PASOS 5, 6 y 8]]
- [[Sesión 2026-09-21 — Limpieza estructural - Track A Fase 2 + Track B completos]]
- [[Sesión 2026-07-03 — Etapa 0 — Seguridad y cimientos - CÓDIGO COMPLETO]]
- [[Sesión 2026-07-13 — Etapa M — Trading cripto en papel, integrado en Khipu (sw v80)]]
- [[Sesión 2026-10-03 — Cierre de Phase 3]]
