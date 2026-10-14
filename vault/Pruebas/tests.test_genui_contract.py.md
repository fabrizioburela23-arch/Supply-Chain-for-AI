---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_genui_contract.py"
lenguaje: "python"
lineas: 240
aliases: ["tests/test_genui_contract.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_genui_contract.py

> Prueba · capa [[Capa Pruebas]] · 240 líneas · `tests/test_genui_contract.py`

## Qué prueba

el sobre `ui` en POST /api/khipu/chat (docs/CHAT_UI_GENERATIVA.md §4.1, §5.6, §8, §11 F1 paso 13). Sin red: la IA es un guion falso y las herramientas leen el snapshot local.

**11** funciones `test_…`.

## Cubre

- [[core.__init__.py]]
- [[core.ai.py]]
- [[core.khipu_chat.py]]
- [[mcp_server.tools.py]]

## Rutas HTTP que llama

1 rutas, de los grupos: [[API khipu]]
