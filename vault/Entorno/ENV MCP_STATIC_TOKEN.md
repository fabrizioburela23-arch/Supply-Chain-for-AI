---
tipo: "variable"
capa: "Infraestructura"
nombre: "MCP_STATIC_TOKEN"
documentada: false
tags: ["capa/infraestructura", "tipo/variable"]
---

# MCP_STATIC_TOKEN

> Variable de entorno · se configura en Railway (Variables). Aquí solo el **nombre**, nunca el valor.

## La leen

- [[core.http.py]] _(en una lista de nombres, p. ej. para tapar secretos en logs)_
- [[mcp_server.api.py]]
- [[mcp_server.auth.py]]

## Pruebas que la fijan o nombran

- [[tests.test_mcp.py]]
- [[tests.test_repair_ops.py]]
- [[tests.test_repair_research.py]]

## ¿Está documentada en CLAUDE.md?

**No** — falta en [[Doc CLAUDE]].
