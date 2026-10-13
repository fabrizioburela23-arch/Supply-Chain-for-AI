---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_server_smoke.py"
lenguaje: "python"
lineas: 303
aliases: ["tests/test_server_smoke.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_server_smoke.py

> Prueba · capa [[Capa Pruebas]] · 303 líneas · `tests/test_server_smoke.py`

## Qué prueba

Khipu Finance smoke tests No API keys required. Tests structure and static responses only. Run: pytest tests/ -v

**24** funciones `test_…`.

## Cubre

- [[core.quotes.py]]
- [[core.voice_api.py]]
- [[data.grafo_v0.json]]
- [[engine.graph3d.js]]
- [[engine.hypergraph.js]]
- [[engine.secondbrain.js]]
- [[engine.timeline3d.js]]
- [[engine.voice.js]]
- [[nodes.links_expand.js]]
- [[nodes.nodes_expand.js]]
- [[nodes.nodes_expand2.js]]
- [[server.py]]
- [[sw.js]]

## Rutas HTTP que llama

9 rutas, de los grupos: [[API ai]], [[API fundamentals]], [[API health]], [[API news]], [[API quote]], [[API quotes]], [[API space]], [[API v1 (pública)]], [[API voice]]

## Variables de entorno que fija o nombra

[[ENV ANTHROPIC_KEY]], [[ENV AV_KEY]], [[ENV DATABASE_URL]], [[ENV FINNHUB_KEY]], [[ENV FMP_KEY]], [[ENV GEMINI_MODEL]], [[ENV MARKETSTACK_KEY]], [[ENV NVIDIA_MODEL]], [[ENV SECRET_KEY]]
