---
tipo: "capa"
capa: "MCP y API"
archivos: 11
tags: ["capa/mcp-api", "tipo/capa"]
---

# Capa MCP y API

> El servidor MCP para IAs externas (herramientas, tokens kmcp_, OAuth) y la pantalla para conectarlas.

**11 archivos · 5.933 líneas.** Volver al [[00 Mapa de Khipus]].

Rutas y herramientas: [[Índice de la API]] · [[API herramientas MCP]].

## Archivos

- [[mcp_server.tools.py]] — 1.877 líneas · catálogo de herramientas MCP de Khipus.
- [[mcp_server.oauth.py]] — 781 líneas · OAuth 2.1 mínimo (y correcto) para conectores remotos.
- [[mcp_server.ops.py]] — 739 líneas · las operaciones MCP que faltaban (ARQUITECTURA_V2 §15; BRECHAS L4-09, decisión #15).
- [[mcp_server.api.py]] — 702 líneas · blueprint mcp_bp (transporte + administración).
- [[mcp_server.auth.py]] — 534 líneas · tokens kmcp_…, alcances, límites por token y auditoría.
- [[engine.mcpconnect.js]] — 500 líneas · 🤖 CONECTAR IAs (MCP): que Claude, ChatGPT, Cursor o un agente propio usen Khipus desde SU propia interfaz.
- [[mcp_server.contract.py]] — 298 líneas · EL contrato común de las respuestas MCP (ARQUITECTURA_V2 §15; BRECHAS L4-08).
- [[mcp_server.protocol.py]] — 208 líneas · JSON-RPC 2.0 + Model Context Protocol (servidor).
- [[scripts.smoke_mcp.py]] — 167 líneas · O1 (misión de reparación 2026-10-04): humo del MCP VIVO (el desplegado en Railway), solo con herramientas de LECTURA.
- [[mcp_server.models.py]] — 106 líneas · tablas del servidor MCP.
- [[mcp_server.__init__.py]] — 21 líneas · servidor MCP (Model Context Protocol) de Khipus (2026-09-30).

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| usa a | [[Capa Infraestructura]] | 22 |
| usa a | [[Capa Ontología y grafo temporal]] | 13 |
| usa a | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 8 |
| usa a | [[Capa Dinero (carteras, trading, corretaje)]] | 6 |
| la usa | [[Capa Infraestructura]] | 4 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 4 |
| la usa | [[Capa Chat y agentes]] | 3 |
| usa a | [[Capa Comité]] | 3 |
| usa a | [[Capa Interfaz (Khipus OS)]] | 3 |
| usa a | [[Capa Investigación]] | 3 |
| la usa | [[Capa Interfaz (Khipus OS)]] | 2 |
| la usa | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 1 |
| la usa | [[Capa Ontología y grafo temporal]] | 1 |
| usa a | [[Capa Datos del catálogo]] | 1 |
| usa a | [[Capa Chat y agentes]] | 1 |
