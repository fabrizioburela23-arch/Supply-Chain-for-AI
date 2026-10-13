---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_infra.py"
lenguaje: "python"
lineas: 1343
aliases: ["tests/test_infra.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_infra.py

> Prueba · capa [[Capa Pruebas]] · 1.343 líneas · `tests/test_infra.py`

## Qué prueba

endurecimiento de infraestructura (auditoría estructural 2026-09-30, grupo INFRA): #1 Dockerfile/exec, #2 hambre de hilos (IA + base), #6 REMIGRATE_ON_BOOT seguro, #13 secretos de IA, #16 railway.toml, #17 motor de matrices acotado, #19 versiones fijadas, #20 escrituras de ontología con PIN, #22 aprobación atómica de propuestas.

**57** funciones `test_…`.

## Cubre

- [[brokerage.models.py]]
- [[core.ai.py]]
- [[core.http.py]]
- [[core.pin.py]]
- [[engine.live.js]]
- [[matrix.api.py]]
- [[matrix.engine.py]]
- [[mcp_server.models.py]]
- [[ontology.actions.py]]
- [[ontology.api.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]
- [[research.models.py]]
- [[scripts.migrate_v0_to_ontology.py]]
- [[server.py]]

## Rutas HTTP que llama

27 rutas, de los grupos: [[API health]], [[API matrix]], [[API ontology]]

## Variables de entorno que fija o nombra

[[ENV AI_BUSY_WAIT_S]], [[ENV AI_MODEL_FAST]], [[ENV AI_ORDER]], [[ENV DATABASE_URL]], [[ENV DB_POOL_SIZE]], [[ENV GEMINI_KEY]], [[ENV MATRIX_BUSY_WAIT_S]], [[ENV RAILWAY_ENVIRONMENT]], [[ENV RAILWAY_ENVIRONMENT_NAME]], [[ENV RAILWAY_PROJECT_ID]], [[ENV REMIGRATE_ON_BOOT]], [[ENV TRADE_PIN]]
