---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_repair_ops.py"
lenguaje: "python"
lineas: 175
aliases: ["tests/test_repair_ops.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_repair_ops.py

> Prueba · capa [[Capa Pruebas]] · 175 líneas · `tests/test_repair_ops.py`

## Qué prueba

O1 (misión de reparación 2026-10-04): humo del MCP vivo (scripts/smoke_mcp.py) + chequeo diario guardado (core/ops_check.py).

**6** funciones `test_…`.

## Cubre

- [[core.http.py]]
- [[core.ops_check.py]]
- [[core.pin.py]]
- [[core.world.py]]
- [[mcp_server.api.py]]
- [[mcp_server.auth.py]]
- [[mcp_server.models.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[research.models.py]]
- [[scripts.smoke_mcp.py]]
- [[server.py]]

## Rutas HTTP que llama

2 rutas, de los grupos: [[API ops]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV KHIPU_MCP_TOKEN]], [[ENV MCP_ALLOWED_HOSTS]], [[ENV MCP_ALLOWED_ORIGINS]], [[ENV MCP_ENABLED]], [[ENV MCP_PUBLIC_URL]], [[ENV MCP_RATE_PER_MIN]], [[ENV MCP_STATIC_TOKEN]], [[ENV TRADE_PIN]]
