---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_voice_agent_split.py"
lenguaje: "python"
lineas: 247
aliases: ["tests/test_voice_agent_split.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_voice_agent_split.py

> Prueba · capa [[Capa Pruebas]] · 247 líneas · `tests/test_voice_agent_split.py`

## Qué prueba

lote I4 (Fase 2+): G5-05 server.py partido sin cambiar comportamiento.

**9** funciones `test_…`.

## Cubre

- [[brokerage.alpaca.py]]
- [[brokerage.models.py]]
- [[core.decision_sites.py]]
- [[core.decisions.py]]
- [[core.http.py]]
- [[core.pin.py]]
- [[core.trading_agent.py]]
- [[core.voice_agent.py]]
- [[core.voice_api.py]]
- [[mcp_server.models.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[research.models.py]]
- [[server.py]]

## Rutas HTTP que llama

11 rutas, de los grupos: [[API trade]], [[API voice]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV ELEVENLABS_AGENT_ID]], [[ENV ELEVENLABS_ALLOW_OVERRIDE]], [[ENV ELEVENLABS_KEY]], [[ENV SECRET_KEY]], [[ENV TRADE_PIN]]
