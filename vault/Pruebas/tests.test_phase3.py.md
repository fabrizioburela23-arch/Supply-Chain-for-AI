---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_phase3.py"
lenguaje: "python"
lineas: 1254
aliases: ["tests/test_phase3.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_phase3.py

> Prueba · capa [[Capa Pruebas]] · 1.254 líneas · `tests/test_phase3.py`

## Qué prueba

PHASE 3 · aprendizaje (resultados + calibración) y comité de inversión con aprobación humana.

**41** funciones `test_…`.

## Cubre

- [[brokerage.models.py]]
- [[brokerage.service.py]]
- [[core.ai.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[research.agents.base.py]]
- [[research.committee.py]]
- [[research.committee_api.py]]
- [[research.deliberation.py]]
- [[research.llm.py]]
- [[research.models.py]]
- [[research.outcomes.py]]
- [[research.runner.py]]
- [[research.schemas.py]]
- [[server.py]]

## Rutas HTTP que llama

12 rutas, de los grupos: [[API committee]]

## Variables de entorno que fija o nombra

[[ENV ALPACA_BASE]], [[ENV ALPACA_KEY]], [[ENV ALPACA_SECRET]], [[ENV BROKERAGE_AUTO_APPROVE_PAPER]], [[ENV BROKERAGE_LIVE_ENABLED]], [[ENV BROKERAGE_TRADING_ENABLED]], [[ENV DATABASE_URL]], [[ENV TRADE_PIN]]
