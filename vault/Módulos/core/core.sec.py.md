---
tipo: "modulo"
capa: "Investigación"
ruta: "core/sec.py"
lenguaje: "python"
lineas: 183
aliases: ["core/sec.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# core/sec.py

> Módulo · capa [[Capa Investigación]] · 183 líneas · `core/sec.py`

## Para qué sirve

SEC EDGAR como EVIDENCIA PRIMARIA (Phase 2).

## API pública

- `resolve_cik(ticker, getter=…)` _(línea 37)_
- `latest_filings(ticker, n=…, getter=…)` — [{form, date, url, description}] más recientes, o []. Solo emisores registrados en la SEC (EE.UU. y extranjeros con ADR que reportan 20-F). _(línea 63)_
- `filing_sections(url, length=…, getter=…)` — {'risk_factors': str, 'mdna': str} (extractos) o {}. _(línea 126)_
- `earnings_dates(ticker, getter=…, years=…)` — Fechas REALES de los reportes trimestrales: 8-K con el ítem 2.02 («Results of Operations») de los últimos `years` años → [(date, … _(línea 146)_

**Internas** (empiezan con `_`): `_cached`, `_strip_html`, `_section`

## Depende de

_Nada interno._

## Lo usan

- [[mcp_server.ops.py]] — lo importa
- [[research.context.py]] — lo importa
- herramienta MCP `simulate_price` → [[API herramientas MCP]]

_Además lo importan 2 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV SEC_USER_AGENT]]

## Pruebas que lo cubren

- [[tests.test_price_sim.py]]
- [[tests.test_sec.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-29 (noche) — TODO EN VIVO + AUDITORÍA DE DATOS FALSOS (sw v161)]]
