---
tipo: "modulo"
capa: "MCP y API"
ruta: "engine/mcpconnect.js"
lenguaje: "javascript"
lineas: 500
aliases: ["engine/mcpconnect.js"]
tags: ["capa/mcp-api", "tipo/modulo"]
---

# engine/mcpconnect.js

> Módulo · capa [[Capa MCP y API]] · 500 líneas · `engine/mcpconnect.js`

## Para qué sirve

🤖 CONECTAR IAs (MCP): que Claude, ChatGPT, Cursor o un agente propio usen Khipus desde SU propia interfaz.

## API pública (globales que define)

`window.KhipuMCP`

## Depende de

- [[app.html]] — usa `LANG`, `_tradeFetch`, `closeSistema`
- [[engine.clients.js]] — usa `KhipuClients`
- [[engine.explain.js]] — usa `explainChip`, `explainRegister`
- [[engine.toast.js]] — usa `KhipuToast`, `khipuActor`

Se carga en [[app.html]] en la posición **63 de 96** (línea 7923), después de [[engine.clients.js]] y antes de [[engine.insights.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 63)
- [[app.html]] — usa `KhipuMCP`
- [[engine.cockpit.js]] — usa `KhipuMCP`
- [[engine.khipu_lang.js]] — usa `KhipuMCP`

## Endpoints que llama

- `DELETE /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `GET /api/brokerage/clients` → [[brokerage.api.py]] ([[API brokerage]])
- `GET /api/mcp/audit` → [[mcp_server.api.py]] ([[API mcp]])
- `GET /api/mcp/status` → [[mcp_server.api.py]] ([[API mcp]])
- `GET /api/mcp/tokens` → [[mcp_server.api.py]] ([[API mcp]])
- `GET /api/mcp/tools` → [[mcp_server.api.py]] ([[API mcp]])
- `GET /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `OPTIONS /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `POST /api/brokerage/clients` → [[brokerage.api.py]] ([[API brokerage]])
- `POST /api/mcp/tokens/<token_id>/revoke` → [[mcp_server.api.py]] ([[API mcp]])
- `POST /api/mcp/tokens` → [[mcp_server.api.py]] ([[API mcp]])
- `POST /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])

## Pruebas que lo cubren

- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_mcp.py]]
- [[tests.test_overnight_ui_small_panels.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-09-30 — PHASE 3 + WORLD MONITOR + CORRETAJE + MCP + ENDURECIMIENTO (sw v170)]]
