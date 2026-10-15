---
tipo: "modulo"
capa: "MCP y API"
ruta: "mcp_server/models.py"
lenguaje: "python"
lineas: 106
aliases: ["mcp_server/models.py"]
tags: ["capa/mcp-api", "tipo/modulo"]
---

# mcp_server/models.py

> Módulo · capa [[Capa MCP y API]] · 106 líneas · `mcp_server/models.py`

## Para qué sirve

tablas del servidor MCP.

## API pública

- clase `McpToken` _(línea 29)_
- clase `McpAudit` _(línea 52)_
- clase `McpOAuthClient` _(línea 70)_
- clase `McpOAuthCode` _(línea 83)_

**Internas** (empiezan con `_`): `_uuid`

## Depende de

- [[ontology.models.py]] — importa `Base`

## Lo usan

- [[mcp_server.api.py]] — lo importa
- [[mcp_server.auth.py]] — lo importa
- [[mcp_server.oauth.py]] — lo importa
- [[ontology.db.py]] — lo importa

_Además lo importan 15 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_catalog_api_pg.py]]
- [[tests.test_cierre_infra.py]]
- [[tests.test_genui_ledger.py]]
- [[tests.test_import_lote2_e2e.py]]
- [[tests.test_import_panel.py]]
- [[tests.test_import_roundtrip.py]]
- [[tests.test_infra.py]]
- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_live_universe_db.py]]
- [[tests.test_mcp.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_repair_ops.py]]
- [[tests.test_rutas_acceso_decision.py]]
- [[tests.test_security.py]]
- [[tests.test_voice_agent_split.py]]
