---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_order_single_path.py"
lenguaje: "python"
lineas: 614
aliases: ["tests/test_order_single_path.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_order_single_path.py

> Prueba · capa [[Capa Pruebas]] · 614 líneas · `tests/test_order_single_path.py`

## Qué prueba

INFRA_OPERATIVA pasos 15-16 (BRECHAS G5-01, M-code-03, G5-08 servidor): UN SOLO CAMINO DE DINERO.

**16** funciones `test_…`.

## Cubre

- [[brokerage.alpaca.py]]
- [[brokerage.models.py]]
- [[brokerage.risk.py]]
- [[brokerage.service.py]]
- [[core.__init__.py]]
- [[core.decisions.py]]
- [[core.http.py]]
- [[core.identity.py]]
- [[core.ledger.py]]
- [[core.pin.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[research.models.py]]
- [[server.py]]

## Rutas HTTP que llama

2 rutas, de los grupos: [[API trade]]

## Variables de entorno que fija o nombra

[[ENV ALPACA_BASE]], [[ENV ALPACA_KEY]], [[ENV ALPACA_SECRET]], [[ENV ANTHROPIC_KEY]], [[ENV BROKERAGE_AUTO_APPROVE_PAPER]], [[ENV BROKERAGE_LIVE_ENABLED]], [[ENV BROKERAGE_TRADING_ENABLED]], [[ENV DATABASE_URL]], [[ENV FINNHUB_KEY]], [[ENV RAILWAY_ENVIRONMENT]], [[ENV RAILWAY_ENVIRONMENT_NAME]], [[ENV RAILWAY_PROJECT_ID]], [[ENV SECRET_KEY]], [[ENV TRADE_PIN]]
