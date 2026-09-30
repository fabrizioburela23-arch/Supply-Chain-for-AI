"""mcp_server/ — servidor MCP (Model Context Protocol) de Khipus (2026-09-30).

Permite que agentes e IAs externas (Claude Code, Claude Desktop, claude.ai,
ChatGPT, Cursor, agentes propios) consulten la ontología, el grafo de la
cadena de suministro y la investigación de Khipus, y que PROPONGAN órdenes a la
cuenta de un cliente — con aprobación HUMANA obligatoria (salvo que
BROKERAGE_AUTO_APPROVE_PAPER=on y el cliente sea de papel).

  protocol.py  JSON-RPC 2.0 / MCP (initialize, tools/list, tools/call…)
  tools.py     catálogo de herramientas (read / research / trade)
  auth.py      tokens kmcp_… (sha256), alcances, límites por token, auditoría
  oauth.py     OAuth 2.1 + PKCE S256 + registro dinámico (conectores remotos)
  models.py    tablas mcp_tokens / mcp_audit / mcp_oauth_clients / mcp_oauth_codes
  api.py       blueprint mcp_bp: /mcp, /api/mcp/*, /.well-known/*, /oauth/*

Todo OPCIONAL: sin DATABASE_URL no hay tokens (solo MCP_STATIC_TOKEN, de
lectura) y la app arranca igual. Ver docs/MCP.md.
"""
SERVER_NAME = 'khipus-finance'
SERVER_TITLE = 'Khipus Finance AI'
SERVER_VERSION = '1.0.0'
