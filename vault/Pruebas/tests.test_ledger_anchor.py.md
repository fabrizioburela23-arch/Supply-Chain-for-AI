---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_ledger_anchor.py"
lenguaje: "python"
lineas: 292
aliases: ["tests/test_ledger_anchor.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_ledger_anchor.py

> Prueba · capa [[Capa Pruebas]] · 292 líneas · `tests/test_ledger_anchor.py`

## Qué prueba

INFRA_OPERATIVA paso 7: ancla diaria, linaje y cadena rota que bloquea el dinero real.

**10** funciones `test_…`.

## Cubre

- [[brokerage.risk.py]]
- [[core.ledger.py]]
- [[core.ledger_api.py]]
- [[core.pin.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]
- [[scripts.fetch_ledger_anchor.py]]
- [[server.py]]

## Rutas HTTP que llama

4 rutas, de los grupos: [[API ledger]]

## Variables de entorno que fija o nombra

[[ENV ALPACA_BASE]], [[ENV BROKERAGE_LIVE_ENABLED]], [[ENV DATABASE_URL]], [[ENV GITHUB_OUTPUT]], [[ENV GITHUB_STEP_SUMMARY]], [[ENV TRADE_PIN]]
