---
tipo: "modulo"
capa: "Investigación"
ruta: "core/sec.py"
lenguaje: "python"
lineas: 143
aliases: ["core/sec.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# core/sec.py

> Módulo · capa [[Capa Investigación]] · 143 líneas · `core/sec.py`

## Para qué sirve

SEC EDGAR como EVIDENCIA PRIMARIA (Phase 2).

## API pública

- `resolve_cik(ticker, getter=…)` _(línea 37)_
- `latest_filings(ticker, n=…, getter=…)` — [{form, date, url, description}] más recientes, o []. Solo emisores registrados en la SEC (EE.UU. y extranjeros con ADR que reportan 20-F). _(línea 63)_
- `filing_sections(url, length=…, getter=…)` — {'risk_factors': str, 'mdna': str} (extractos) o {}. _(línea 126)_

**Internas** (empiezan con `_`): `_cached`, `_strip_html`, `_section`

## Depende de

_Nada interno._

## Lo usan

- [[research.context.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV SEC_USER_AGENT]]

## Pruebas que lo cubren

- [[tests.test_sec.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-29 (noche) — TODO EN VIVO + AUDITORÍA DE DATOS FALSOS (sw v161)]]
