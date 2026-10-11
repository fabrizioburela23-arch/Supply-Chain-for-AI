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
- [[server.py]]

## Pruebas que la fijan o nombran

- [[tests.test_ai_usage.py]]
- [[tests.test_brokerage.py]]
- [[tests.test_infra.py]]
- [[tests.test_mcp.py]]
- [[tests.test_overnight_voice_server.py]]
- [[tests.test_phase3.py]]
- [[tests.test_reconcile.py]]
- [[tests.test_repair_ontology_review.py]]
- [[tests.test_repair_ops.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_security.py]]

## ¿Está documentada en CLAUDE.md?

Sí — en la lista **Variables de entorno** de [[Doc CLAUDE]].

## Mencionada en sesiones

- [[Sesión 2026-09-21 — Limpieza estructural - Track A Fase 2 + Track B completos]]
- [[Sesión 2026-07-03 — Etapa 0 — Seguridad y cimientos - CÓDIGO COMPLETO]]
- [[Sesión 2026-07-13 — Etapa M — Trading cripto en papel, integrado en Khipu (sw v80)]]
- [[Sesión 2026-10-03 — Cierre de Phase 3]]
