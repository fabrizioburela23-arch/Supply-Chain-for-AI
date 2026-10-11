---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_repair_review2.py"
lenguaje: "python"
lineas: 171
aliases: ["tests/test_repair_review2.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_repair_review2.py

> Prueba · capa [[Capa Pruebas]] · 171 líneas · `tests/test_repair_review2.py`

## Qué prueba

G6b: segunda revisión adversarial (lente "contratos y operación") sobre G6/O1/O2. Cada test reproduce un hallazgo.

**9** funciones `test_…`.

## Cubre

- [[core.entities.py]]
- [[core.http.py]]
- [[core.khipu_chat.py]]
- [[core.pin.py]]
- [[matrix.engine.py]]
- [[mcp_server.auth.py]]
- [[mcp_server.tools.py]]
- [[ontology.actions.py]]
- [[ontology.api.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]
- [[research.committee.py]]
- [[research.models.py]]
- [[research.runner.py]]
- [[server.py]]

## Rutas HTTP que llama

2 rutas, de los grupos: [[API ontology]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV LOG_JSON]], [[ENV TRADE_PIN]]
