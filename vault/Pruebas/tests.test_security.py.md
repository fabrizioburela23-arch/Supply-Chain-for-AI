---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_security.py"
lenguaje: "python"
lineas: 1040
aliases: ["tests/test_security.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_security.py

> Prueba · capa [[Capa Pruebas]] · 1.040 líneas · `tests/test_security.py`

## Qué prueba

rutas de DINERO y endurecimiento estructural (auditoría 2026-09-30).

**59** funciones `test_…`.

## Cubre

- [[brokerage.api.py]]
- [[brokerage.crypto.py]]
- [[brokerage.models.py]]
- [[brokerage.service.py]]
- [[core.http.py]]
- [[core.pin.py]]
- [[mcp_server.api.py]]
- [[mcp_server.auth.py]]
- [[mcp_server.models.py]]
- [[mcp_server.oauth.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[research.committee_api.py]]
- [[server.py]]

## Rutas HTTP que llama

25 rutas, de los grupos: [[API MCP transporte y OAuth]], [[API brokerage]], [[API committee]], [[API health]], [[API mcp]], [[API news]], [[API scalp]], [[API trade]], [[API voice]], [[API ws-key]], [[API ws-token]]

## Variables de entorno que fija o nombra

[[ENV ALPACA_BASE]], [[ENV ALPACA_KEY]], [[ENV ALPACA_SECRET]], [[ENV ANTHROPIC_KEY]], [[ENV BROKERAGE_ENC_KEY]], [[ENV BROKERAGE_TRADING_ENABLED]], [[ENV DATABASE_URL]], [[ENV ELEVENLABS_ALLOW_OVERRIDE]], [[ENV ELEVENLABS_KEY]], [[ENV FINNHUB_KEY]], [[ENV FINNHUB_WS_KEY]], [[ENV GEMINI_KEY]], [[ENV KHIPU_ADMIN_SECRET]], [[ENV MCP_PIN_LOCK_MIN]], [[ENV MCP_PIN_MAX_FAILS]], [[ENV MCP_TRUSTED_PROXY_HOPS]], [[ENV NVIDIA_KEY]], [[ENV RAILWAY_ENVIRONMENT]], [[ENV RAILWAY_ENVIRONMENT_NAME]], [[ENV RAILWAY_PROJECT_ID]], [[ENV SECRET_KEY]], [[ENV TAVILY_KEY]], [[ENV TRADE_PIN]]
