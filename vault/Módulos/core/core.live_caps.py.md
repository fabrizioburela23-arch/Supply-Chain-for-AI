---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/live_caps.py"
lenguaje: "python"
lineas: 127
aliases: ["core/live_caps.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/live_caps.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 127 líneas · `core/live_caps.py`

## Para qué sirve

capitalización EN VIVO de TODAS las cotizadas del grafo.

## API pública

- `refresh(fetch=…)` — Consulta todas las cotizadas (bloqueante). `fetch` inyectable en tests. _(línea 32)_
- `get_caps(start=…)` — Estado actual; si está vencido lanza un refresco en segundo plano. _(línea 118)_

**Internas** (empiezan con `_`): `_symbols_by_id`, `_daily_outcomes`

## Depende de

- [[core.entities.py]] — importa `get_index`
- [[core.quotes.py]] — importa `fetch_quotes_batch_yahoo`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[research.auto_events.py]] — importa `dispatch_earnings`, `dispatch_price_anomalies`
- [[research.outcomes.py]] — importa `evaluate_due`

## Lo usan

- [[core.khipu_chat.py]] — lo importa
- [[core.live_fundamentals.py]] — lo importa
- [[core.portfolio_ai.py]] — lo importa
- [[matrix.tensor.py]] — lo importa
- [[research.health.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 5 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_live_caps.py]]
- [[tests.test_repair_committee.py]]
- [[tests.test_repair_prices.py]]
- [[tests.test_tensor.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-29 (noche) — TODO EN VIVO + AUDITORÍA DE DATOS FALSOS (sw v161)]]
