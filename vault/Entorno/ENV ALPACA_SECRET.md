---
tipo: "variable"
capa: "Infraestructura"
nombre: "ALPACA_SECRET"
documentada: true
tags: ["capa/infraestructura", "tipo/variable"]
---

# ALPACA_SECRET

> Variable de entorno · se configura en Railway (Variables). Aquí solo el **nombre**, nunca el valor.

## La leen

- [[brokerage.alpaca.py]]
- [[core.http.py]] _(en una lista de nombres, p. ej. para tapar secretos en logs)_
- [[server.py]]

## Pruebas que la fijan o nombran

- [[tests.test_brokerage.py]]
- [[tests.test_ledger_callsites.py]]
- [[tests.test_mcp.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_overnight3_diag_bilingual.py]]
- [[tests.test_phase3.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_review_batch_g.py]]
- [[tests.test_security.py]]
- [[tests.test_trading_agent_ledger.py]]

## ¿Está documentada en CLAUDE.md?

Sí — en la lista **Variables de entorno** de [[Doc CLAUDE]].
