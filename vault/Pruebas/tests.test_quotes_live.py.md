---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_quotes_live.py"
lenguaje: "python"
lineas: 322
aliases: ["tests/test_quotes_live.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_quotes_live.py

> Prueba · capa [[Capa Pruebas]] · 322 líneas · `tests/test_quotes_live.py`

## Qué prueba

Precios EN VIVO por lotes (2026-10-04): core.quotes.fetch_quotes_live + rutas /api/quote, /api/quotes, /api/quotes/live, /api/market/providers. Sin red: el registro de proveedores se reemplaza por uno falso.

**18** funciones `test_…`.

## Cubre

- [[core.config.py]]
- [[core.providers.base.py]]
- [[core.providers.market.py]]
- [[core.quotes.py]]
- [[server.py]]

## Rutas HTTP que llama

4 rutas, de los grupos: [[API market]], [[API quote]], [[API quotes]]

## Variables de entorno que fija o nombra

[[ENV ANTHROPIC_KEY]], [[ENV AV_KEY]], [[ENV FINNHUB_KEY]], [[ENV FMP_KEY]], [[ENV MARKETSTACK_KEY]], [[ENV SECRET_KEY]]
