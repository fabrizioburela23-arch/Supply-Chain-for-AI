---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/gpr.py"
lenguaje: "python"
lineas: 186
aliases: ["core/gpr.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/gpr.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 186 líneas · `core/gpr.py`

## Para qué sirve

Índice de RIESGO GEOPOLÍTICO (GPR) de Caldara & Iacoviello (Junta de la Reserva Federal), EN VIVO y gratuito: https://www.matteoiacoviello.com/gpr.htm

## API pública

- `parse_daily(rows, datemode=…)` _(línea 89)_
- `parse_monthly(rows, datemode=…)` _(línea 111)_
- `gpr_cached()` — Lo que haya en caché (sin red): para el MCP y la mezcla con las capas de países. _(línea 148)_
- `gpr(force=…)` — {ok, daily{…}, monthly{…}|None, source, url, as_of} o {ok: False, error_code…}. Caché 12 h. _(línea 154)_

**Internas** (empiezan con `_`): `_xls_rows`, `_header`, `_date_of`, `_num`, `_get`

## Depende de

_Nada interno._

## Lo usan

- [[core.world.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[research.agent_skills.py]] — lo importa
- herramienta MCP `get_world_events` → [[API herramientas MCP]]

_Además lo importan 1 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV WORLD_GPR_DAILY_URL]]
- [[ENV WORLD_GPR_MONTHLY_URL]]

## Pruebas que lo cubren

- [[tests.test_gpr.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (u) — ÍNDICE GPR (Caldara-Iacoviello) EN VIVO (sw v227)]]
