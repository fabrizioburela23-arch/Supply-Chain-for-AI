---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_replay_determinism.py"
lenguaje: "python"
lineas: 489
aliases: ["tests/test_replay_determinism.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_replay_determinism.py

> Prueba · capa [[Capa Pruebas]] · 489 líneas · `tests/test_replay_determinism.py`

## Qué prueba

INFRA_OPERATIVA paso 24 (§5.6): repetir decisiones pasadas.

**15** funciones `test_…`.

## Cubre

- [[brokerage.models.py]]
- [[brokerage.service.py]]
- [[core.__init__.py]]
- [[core.ai_calls.py]]
- [[core.decisions.py]]
- [[core.governance.py]]
- [[core.governance_flow.py]]
- [[core.http.py]]
- [[core.identity.py]]
- [[core.impls.py]]
- [[core.ledger_api.py]]
- [[core.pin.py]]
- [[core.replay.py]]
- [[matrix.api.py]]
- [[matrix.engine.py]]
- [[mcp_server.tools.py]]
- [[ontology.actions.py]]
- [[ontology.bitemporal.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]
- [[research.committee.py]]
- [[research.llm.py]]
- [[research.models.py]]
- [[server.py]]

## Rutas HTTP que llama

6 rutas, de los grupos: [[API ledger]], [[API matrix]]

## Variables de entorno que fija o nombra

[[ENV ALPACA_BASE]], [[ENV ALPACA_KEY]], [[ENV ALPACA_SECRET]], [[ENV BROKERAGE_AUTO_APPROVE_PAPER]], [[ENV BROKERAGE_LIVE_ENABLED]], [[ENV BROKERAGE_TRADING_ENABLED]], [[ENV DATABASE_URL]], [[ENV RAILWAY_ENVIRONMENT]], [[ENV RAILWAY_ENVIRONMENT_NAME]], [[ENV RAILWAY_PROJECT_ID]], [[ENV SECRET_KEY]], [[ENV TRADE_PIN]]
