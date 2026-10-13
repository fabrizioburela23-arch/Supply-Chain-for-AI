---
tipo: "modulo"
capa: "MCP y API"
ruta: "scripts/smoke_mcp.py"
lenguaje: "python"
lineas: 167
aliases: ["scripts/smoke_mcp.py"]
tags: ["capa/mcp-api", "tipo/modulo"]
---

# scripts/smoke_mcp.py

> Módulo · capa [[Capa MCP y API]] · 167 líneas · `scripts/smoke_mcp.py`

## Para qué sirve

O1 (misión de reparación 2026-10-04): humo del MCP VIVO (el desplegado en Railway), solo con herramientas de LECTURA.

## API pública

- clase `SmokeConfigError` _(línea 43)_
- `smoke(base_url, token, http=…, timeout=…)` _(línea 67)_
- `main(argv=…)` _(línea 131)_

**Internas** (empiezan con `_`): `_rpc`

## Depende de

_Nada interno._

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

_Además lo importan 1 pruebas (lista abajo)._

## Endpoints que llama

- `DELETE /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `GET /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `OPTIONS /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `POST /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])

## Variables de entorno que lee (solo nombres)

- [[ENV KHIPU_MCP_TOKEN]]
- [[ENV KHIPU_URL]]
- [[ENV SMOKE_RETRIES]]

## Pruebas que lo cubren

- [[tests.test_block0_ci.py]]
- [[tests.test_repair_ops.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-04 (i) — MISIÓN DE REPARACIÓN P1 GRAFO + P2 WORLD MONITOR Y OPERACIÓN]]
