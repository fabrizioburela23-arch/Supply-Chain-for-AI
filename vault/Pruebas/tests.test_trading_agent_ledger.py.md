---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_trading_agent_ledger.py"
lenguaje: "python"
lineas: 241
aliases: ["tests/test_trading_agent_ledger.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_trading_agent_ledger.py

> Prueba · capa [[Capa Pruebas]] · 241 líneas · `tests/test_trading_agent_ledger.py`

## Qué prueba

INFRA_OPERATIVA paso 16 (BRECHAS G5-10, MAP D #12, #14): el agente de trading del servidor por EL camino único y con memoria.

**8** funciones `test_…`.

## Cubre

- [[brokerage.models.py]]
- [[brokerage.service.py]]
- [[core.http.py]]
- [[core.pin.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[research.models.py]]
- [[server.py]]

## Rutas HTTP que llama

2 rutas, de los grupos: [[API trade]]

## Variables de entorno que fija o nombra

[[ENV ALPACA_BASE]], [[ENV ALPACA_KEY]], [[ENV ALPACA_SECRET]], [[ENV BROKERAGE_LIVE_ENABLED]], [[ENV BROKERAGE_TRADING_ENABLED]], [[ENV DATABASE_URL]], [[ENV RAILWAY_ENVIRONMENT]], [[ENV SECRET_KEY]], [[ENV TRADE_PIN]]
