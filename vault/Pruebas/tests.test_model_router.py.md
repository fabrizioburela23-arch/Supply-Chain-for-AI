---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_model_router.py"
lenguaje: "python"
lineas: 83
aliases: ["tests/test_model_router.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_model_router.py

> Prueba · capa [[Capa Pruebas]] · 83 líneas · `tests/test_model_router.py`

## Qué prueba

Router de modelos del chat (core/model_router, 2026-11-07): Jev elige pequeño / mediano / frontera; si Jev no llega, reglas instantáneas. Pequeño = pasos con Haiku; frontera = respuesta final con Opus.

**4** funciones `test_…`.

## Cubre

- [[core.ai.py]]
- [[core.decide.py]]
- [[core.khipu_chat.py]]
- [[core.live_facts.py]]
- [[core.model_router.py]]
- [[mcp_server.tools.py]]

## Variables de entorno que fija o nombra

[[ENV AI_MODEL_FRONTIER]], [[ENV AI_MODEL_SMALL]], [[ENV AI_ROUTER]], [[ENV DECIDE_CONTROL]], [[ENV TYPESAFE_API_KEY]], [[ENV TYPESAFE_KEY]]
