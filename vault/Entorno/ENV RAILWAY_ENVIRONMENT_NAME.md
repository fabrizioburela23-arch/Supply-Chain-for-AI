---
tipo: "variable"
capa: "Infraestructura"
nombre: "RAILWAY_ENVIRONMENT_NAME"
documentada: false
tags: ["capa/infraestructura", "tipo/variable"]
---

# RAILWAY_ENVIRONMENT_NAME

> Variable de entorno · se configura en Railway (Variables). Aquí solo el **nombre**, nunca el valor.

## La leen

- [[brokerage.crypto.py]] _(en una lista de nombres, p. ej. para tapar secretos en logs)_
- [[core.pin.py]] _(en una lista de nombres, p. ej. para tapar secretos en logs)_
- [[scripts.migrate_v0_to_ontology.py]] _(en una lista de nombres, p. ej. para tapar secretos en logs)_

## Pruebas que la fijan o nombran

- [[tests.test_infra.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_core.py]]
- [[tests.test_ledger_privacy.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_security.py]]

## ¿Está documentada en CLAUDE.md?

**No** — falta en [[Doc CLAUDE]].
