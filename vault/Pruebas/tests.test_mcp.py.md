---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_mcp.py"
lenguaje: "python"
lineas: 1506
aliases: ["tests/test_mcp.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_mcp.py

> Prueba · capa [[Capa Pruebas]] · 1.506 líneas · `tests/test_mcp.py`

## Qué prueba

servidor MCP (mcp_server/): protocolo, auth, alcances, herramientas, flujo de trading con aprobación humana, auditoría y OAuth.

**60** funciones `test_…`.

## Cubre

- [[brokerage.alpaca.py]]
- [[brokerage.service.py]]
- [[core.ai.py]]
- [[core.http.py]]
- [[core.options.py]]
- [[core.risk_report.py]]
- [[core.world.py]]
- [[engine.mcpconnect.js]]
- [[mcp_server.api.py]]
- [[mcp_server.auth.py]]
- [[mcp_server.models.py]]
- [[mcp_server.oauth.py]]
- [[mcp_server.protocol.py]]
- [[mcp_server.tools.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[research.committee.py]]
- [[research.models.py]]
- [[research.runner.py]]

## Rutas HTTP que llama

13 rutas, de los grupos: [[API MCP transporte y OAuth]], [[API mcp]]

## Variables de entorno que fija o nombra

[[ENV ALPACA_BASE]], [[ENV ALPACA_KEY]], [[ENV ALPACA_SECRET]], [[ENV BROKERAGE_AUTO_APPROVE_PAPER]], [[ENV BROKERAGE_ENC_KEY]], [[ENV BROKERAGE_LIVE_ENABLED]], [[ENV BROKERAGE_TRADING_ENABLED]], [[ENV DATABASE_URL]], [[ENV MCP_ALLOWED_HOSTS]], [[ENV MCP_ALLOWED_ORIGINS]], [[ENV MCP_ENABLED]], [[ENV MCP_MAX_INFLIGHT]], [[ENV MCP_MAX_INFLIGHT_TOTAL]], [[ENV MCP_OAUTH_ENABLED]], [[ENV MCP_PIN_LOCK_MIN]], [[ENV MCP_PIN_MAX_FAILS]], [[ENV MCP_PUBLIC_URL]], [[ENV MCP_RATE_PER_MIN]], [[ENV MCP_STATIC_TOKEN]], [[ENV MCP_TRADING_ENABLED]], [[ENV MCP_TRUSTED_PROXY_HOPS]], [[ENV RAILWAY_PUBLIC_DOMAIN]], [[ENV RESEARCH_DAILY_BUDGET_USD]], [[ENV TRADE_PIN]]
