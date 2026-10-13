---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_brokerage.py"
lenguaje: "python"
lineas: 1482
aliases: ["tests/test_brokerage.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_brokerage.py

> Prueba · capa [[Capa Pruebas]] · 1.482 líneas · `tests/test_brokerage.py`

## Qué prueba

corretaje multi-cliente (brokerage/).

**50** funciones `test_…`.

## Cubre

- [[brokerage.alpaca.py]]
- [[brokerage.api.py]]
- [[brokerage.crypto.py]]
- [[brokerage.models.py]]
- [[brokerage.risk.py]]
- [[brokerage.service.py]]
- [[core.http.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[research.committee.py]]
- [[research.models.py]]

## Rutas HTTP que llama

18 rutas, de los grupos: [[API brokerage]]

## Variables de entorno que fija o nombra

[[ENV ALPACA_BASE]], [[ENV ALPACA_KEY]], [[ENV ALPACA_OAUTH_CLIENT_ID]], [[ENV ALPACA_OAUTH_CLIENT_SECRET]], [[ENV ALPACA_OAUTH_REDIRECT_URI]], [[ENV ALPACA_SECRET]], [[ENV BROKERAGE_AUTO_APPROVE_PAPER]], [[ENV BROKERAGE_ENC_KEY]], [[ENV BROKERAGE_LIVE_ENABLED]], [[ENV BROKERAGE_TRADING_ENABLED]], [[ENV DATABASE_URL]], [[ENV SECRET_KEY]], [[ENV TRADE_PIN]]
