---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_rutas_acceso_decision.py"
lenguaje: "python"
lineas: 300
aliases: ["tests/test_rutas_acceso_decision.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_rutas_acceso_decision.py

> Prueba · capa [[Capa Pruebas]] · 300 líneas · `tests/test_rutas_acceso_decision.py`

## Qué prueba

lote I1 (Fase 2+): las últimas rutas de escritura fuera de la voz dejan su decisión (docs/CIERRE_INFRA.md §3; tests/test_cierre_infra.py SIN_DECISION solo se achica):

**7** funciones `test_…`.

## Cubre

- [[core.decisions.py]]
- [[core.http.py]]
- [[core.replay.py]]
- [[core.sim_agents.py]]
- [[mcp_server.api.py]]
- [[mcp_server.auth.py]]
- [[mcp_server.models.py]]
- [[mcp_server.oauth.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[research.models.py]]
- [[server.py]]

## Rutas HTTP que llama

7 rutas, de los grupos: [[API MCP transporte y OAuth]], [[API mcp]], [[API sim]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV MCP_ENABLED]], [[ENV MCP_OAUTH_ENABLED]], [[ENV MCP_PIN_MAX_FAILS]], [[ENV MCP_PUBLIC_URL]], [[ENV MCP_STATIC_TOKEN]], [[ENV SECRET_KEY]], [[ENV TRADE_PIN]]
