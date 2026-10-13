---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_mcp_contract.py"
lenguaje: "python"
lineas: 128
aliases: ["tests/test_mcp_contract.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_mcp_contract.py

> Prueba · capa [[Capa Pruebas]] · 128 líneas · `tests/test_mcp_contract.py`

## Qué prueba

contrato común de las respuestas MCP (mcp_server/contract.py; BRECHAS L4-08): detail (summary|standard|full) y max_chars en TODAS las herramientas, recorte ORDENADO con marcas, campos del contrato y tamaños acotados (get_supply_chain de Nvidia a 2 saltos: antes 112k caracteres ×2). Sin red, sin base.

**9** funciones `test_…`.

## Cubre

- [[core.khipu_chat.py]]
- [[mcp_server.auth.py]]
- [[mcp_server.contract.py]]
- [[mcp_server.protocol.py]]
- [[mcp_server.tools.py]]
