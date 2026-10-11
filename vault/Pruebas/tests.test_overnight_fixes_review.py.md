---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_overnight_fixes_review.py"
lenguaje: "python"
lineas: 373
aliases: ["tests/test_overnight_fixes_review.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_overnight_fixes_review.py

> Prueba · capa [[Capa Pruebas]] · 373 líneas · `tests/test_overnight_fixes_review.py`

## Qué prueba

Overnight 2026-10-10 — arreglos de la revisión (fixer). Cada test fallaba antes del arreglo.

**20** funciones `test_…`.

## Cubre

- [[core.ai.py]]
- [[core.ai_usage.py]]
- [[core.config.py]]
- [[core.decide.py]]
- [[core.http.py]]
- [[core.khipu_chat.py]]
- [[core.live_facts.py]]
- [[core.voice_agent.py]]
- [[engine.khipu_chat.js]]
- [[engine.portfolios.js]]
- [[engine.riskreport.js]]
- [[engine.voice.js]]
- [[mcp_server.tools.py]]
- [[research.llm.py]]
- [[server.py]]

## Rutas HTTP que llama

3 rutas, de los grupos: [[API ai]], [[API thesis]], [[API voice]]

## Variables de entorno que fija o nombra

[[ENV AI_MODEL_DEEP]], [[ENV AI_MODEL_FAST]], [[ENV DECIDE_CONTROL]], [[ENV ELEVENLABS_AGENT_ID]], [[ENV ELEVENLABS_KEY]], [[ENV SECRET_KEY]], [[ENV TYPESAFE_API_KEY]]
