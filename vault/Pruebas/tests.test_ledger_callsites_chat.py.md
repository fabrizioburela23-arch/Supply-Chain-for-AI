---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_ledger_callsites_chat.py"
lenguaje: "python"
lineas: 312
aliases: ["tests/test_ledger_callsites_chat.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_ledger_callsites_chat.py

> Prueba · capa [[Capa Pruebas]] · 312 líneas · `tests/test_ledger_callsites_chat.py`

## Qué prueba

INFRA_OPERATIVA §2.5, paso 20: decisiones ASYNC de chat, Jev, MCP, qué-pasaría-si e insights (la parte de dinero/comité/investigación vive en tests/test_ledger_callsites.py).

**8** funciones `test_…`.

## Cubre

- [[core.__init__.py]]
- [[core.ai.py]]
- [[core.ai_calls.py]]
- [[core.decide.py]]
- [[core.decisions.py]]
- [[core.http.py]]
- [[core.khipu_chat.py]]
- [[core.live_facts.py]]
- [[matrix.api.py]]
- [[mcp_server.api.py]]
- [[mcp_server.auth.py]]
- [[mcp_server.models.py]]
- [[mcp_server.tools.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[research.models.py]]
- [[server.py]]

## Rutas HTTP que llama

3 rutas, de los grupos: [[API MCP transporte y OAuth]], [[API khipu]], [[API mcp]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV MCP_ALLOWED_HOSTS]], [[ENV MCP_ALLOWED_ORIGINS]], [[ENV MCP_ENABLED]], [[ENV MCP_STATIC_TOKEN]], [[ENV SECRET_KEY]], [[ENV TRADE_PIN]], [[ENV TYPESAFE_API_KEY]]
