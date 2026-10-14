---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_genui_rivals.py"
lenguaje: "python"
lineas: 92
aliases: ["tests/test_genui_rivals.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_genui_rivals.py

> Prueba · capa [[Capa Pruebas]] · 92 líneas · `tests/test_genui_rivals.py`

## Qué prueba

«ganadores» de un choque en el SERVIDOR (core/genui/rivals.py) = el MISMO resultado que KhipuHot.rivals del navegador (engine/hotclient.js), sobre las mismas entradas (docs/CHAT_UI_GENERATIVA.md §5.2, F1 paso 11). Se corre el JS real en node con el catálogo real; impactos y capitalizaciones al azar (semilla fija). Y run_scenario (mcp_server/ops.py) los devuelve calculados sobre TODOS los impactos del kernel.

**3** funciones `test_…`.

## Cubre

- [[core.__init__.py]]
- [[data.grafo_v0.json]]
- [[engine.hotclient.js]]
- [[mcp_server.auth.py]]
- [[mcp_server.ops.py]]
- [[mcp_server.tools.py]]
