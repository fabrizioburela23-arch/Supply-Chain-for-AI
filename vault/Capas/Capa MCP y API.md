---
tipo: "capa"
capa: "MCP y API"
archivos: 9
tags: ["capa/mcp-api", "tipo/capa"]
---

# Capa MCP y API

> El servidor MCP para IAs externas (herramientas, tokens kmcp_, OAuth) y la pantalla para conectarlas.

**9 archivos · 4.569 líneas.** Volver al [[00 Mapa de Khipus]].

Rutas y herramientas: [[Índice de la API]] · [[API herramientas MCP]].

## Archivos

- [[mcp_server.tools.py]] — 1.726 líneas · catálogo de herramientas MCP de Khipus.
- [[mcp_server.oauth.py]] — 708 líneas · OAuth 2.1 mínimo (y correcto) para conectores remotos.
- [[mcp_server.api.py]] — 609 líneas · blueprint mcp_bp (transporte + administración).
- [[mcp_server.auth.py]] — 534 líneas · tokens kmcp_…, alcances, límites por token y auditoría.
- [[engine.mcpconnect.js]] — 500 líneas · 🤖 CONECTAR IAs (MCP): que Claude, ChatGPT, Cursor o un agente propio usen Khipus desde SU propia interfaz.
- [[mcp_server.protocol.py]] — 203 líneas · JSON-RPC 2.0 + Model Context Protocol (servidor).
- [[scripts.smoke_mcp.py]] — 162 líneas · O1 (misión de reparación 2026-10-04): humo del MCP VIVO (el desplegado en Railway), solo con herramientas de LECTURA.
- [[mcp_server.models.py]] — 106 líneas · tablas del servidor MCP.
- [[mcp_server.__init__.py]] — 21 líneas · servidor MCP (Model Context Protocol) de Khipus (2026-09-30).

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| usa a | [[Capa Ontología y grafo temporal]] | 11 |
| usa a | [[Capa Infraestructura]] | 10 |
| usa a | [[Capa Dinero (carteras, trading, corretaje)]] | 6 |
| la usa | [[Capa Infraestructura]] | 4 |
| la usa | [[Capa Chat y agentes]] | 3 |
| usa a | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 3 |
| usa a | [[Capa Interfaz (Khipus OS)]] | 3 |
| usa a | [[Capa Investigación]] | 3 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 3 |
| la usa | [[Capa Interfaz (Khipus OS)]] | 2 |
| usa a | [[Capa Comité]] | 2 |
| la usa | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 1 |
| la usa | [[Capa Ontología y grafo temporal]] | 1 |
| usa a | [[Capa Datos del catálogo]] | 1 |
