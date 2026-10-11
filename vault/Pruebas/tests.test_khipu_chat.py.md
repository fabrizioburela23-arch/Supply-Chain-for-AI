---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_khipu_chat.py"
lenguaje: "python"
lineas: 464
aliases: ["tests/test_khipu_chat.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_khipu_chat.py

> Prueba · capa [[Capa Pruebas]] · 464 líneas · `tests/test_khipu_chat.py`

## Qué prueba

Cerebro conversacional de Khipu (core/khipu_chat.py) + enrutador del cliente (engine/khipu_chat.js). Sin red: la IA es un guion falso (monkeypatch de core.ai._ai_complete) y las herramientas usadas leen el snapshot local.

**30** funciones `test_…`.

## Cubre

- [[core.ai.py]]
- [[core.khipu_chat.py]]
- [[data.grafo_v0.json]]
- [[engine.cockpit.js]]
- [[engine.khipu_chat.js]]
- [[engine.khipu_lang.js]]
- [[mcp_server.tools.py]]

## Rutas HTTP que llama

2 rutas, de los grupos: [[API khipu]]
