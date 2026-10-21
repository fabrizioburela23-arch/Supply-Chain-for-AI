---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/live_caps.py"
lenguaje: "python"
lineas: 191
aliases: ["core/live_caps.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/live_caps.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 191 líneas · `core/live_caps.py`

## Para qué sirve

capitalización EN VIVO de TODAS las cotizadas del grafo.

## API pública

- `phase_state()` — Cuántos símbolos tiene el universo, cuántos nuevos ya entraron y cuántos esperan su tanda. _(línea 51)_
- `refresh(fetch=…)` — Consulta todas las cotizadas (bloqueante). `fetch` inyectable en tests. _(línea 73)_
- `get_caps(start=…)` — Estado actual; si está vencido lanza un refresco en segundo plano. _(línea 180)_

**Internas** (empiezan con `_`): `_symbols_by_id`, `_phase`, `_caps_of`, `_daily_outcomes`

## Depende de

- [[core.instruments.py]] — importa `instruments`
- [[core.quotes.py]] — importa `YAHOO_BATCH_CHUNK`, `fetch_quotes_batch_yahoo`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[research.auto_events.py]] — importa `dispatch_earnings`, `dispatch_price_anomalies`
- [[research.outcomes.py]] — importa `evaluate_due`

## Lo usan

- [[core.khipu_chat.py]] — lo importa
- [[core.live_fundamentals.py]] — lo importa
- [[core.portfolio_ai.py]] — lo importa
- [[core.prices_store.py]] — lo importa
- [[core.sim_report.py]] — lo importa
- [[matrix.tensor.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- [[research.health.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `run_scenario` → [[API herramientas MCP]]

_Además lo importan 8 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_live_caps.py]]
- [[tests.test_live_universe.py]]
- [[tests.test_live_universe_db.py]]
- [[tests.test_lotel_fixer.py]]
- [[tests.test_repair_committee.py]]
- [[tests.test_repair_prices.py]]
- [[tests.test_tensor.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-29 (noche) — TODO EN VIVO + AUDITORÍA DE DATOS FALSOS (sw v161)]]
