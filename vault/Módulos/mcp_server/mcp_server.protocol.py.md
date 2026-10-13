---
tipo: "modulo"
capa: "MCP y API"
ruta: "mcp_server/protocol.py"
lenguaje: "python"
lineas: 208
aliases: ["mcp_server/protocol.py"]
tags: ["capa/mcp-api", "tipo/modulo"]
---

# mcp_server/protocol.py

> Módulo · capa [[Capa MCP y API]] · 208 líneas · `mcp_server/protocol.py`

## Para qué sirve

JSON-RPC 2.0 + Model Context Protocol (servidor).

## API pública

- `negotiate(requested)` _(línea 38)_
- `error(id_, code, message, data=…)` _(línea 42)_
- `result(id_, res)` _(línea 49)_
- `instructions(principal)` _(línea 53)_
- `handle(msg, ctx)` — → (respuesta dict | None, audit dict | None). _(línea 118)_

**Internas** (empiezan con `_`): `_is_valid_id`, `_finite`, `_tool_result`

## Depende de

- [[mcp_server.__init__.py]] — importa `SERVER_NAME`, `SERVER_TITLE`, `SERVER_VERSION`
- [[mcp_server.tools.py]] — importa `tools`

## Lo usan

- [[mcp_server.api.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_mcp.py]]
- [[tests.test_mcp_contract.py]]
