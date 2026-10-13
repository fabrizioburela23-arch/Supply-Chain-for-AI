---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/quotes.py"
lenguaje: "python"
lineas: 463
aliases: ["core/quotes.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/quotes.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 463 líneas · `core/quotes.py`

## Para qué sirve

cotización cruda compartida (server rutas + agentes de alertas).

## API pública

- `finnhub_quota_active()` — True mientras Finnhub está en pausa por cuota (HTTP 429). _(línea 36)_
- `finnhub_pause(seconds=…)` _(línea 42)_
- `finnhub_resume()` — Cierra el circuito (tests / reinicio manual). _(línea 49)_
- `finnhub_circuit_state()` _(línea 55)_
- `is_intl(symbol)` — ¿Símbolo de bolsa no-estadounidense? (sufijo Yahoo: 688825.SS, 1347.HK…) Finnhub free no los cubre — van directo a Yahoo, sin quemar la … _(línea 80)_
- `fetch_quote_intl(symbol, timeout=…)` — Cotización de CUALQUIER bolsa del mundo vía Yahoo, SIEMPRE en USD. Devuelve {close, prev, live, pct, vol, currency, converted, ts, … _(línea 108)_
- `fetch_market_cap_yahoo(symbol, timeout=…)` — Capitalización en MILES DE MILLONES de USD vía Yahoo, o None. Cacheada 6 h por símbolo (cambia despacio y no conviene martillar). _(línea 179)_
- `fetch_quotes_batch_yahoo(symbols, chunk=…, timeout=…)` — Cotización + capitalización EN LOTE (Yahoo v7 quote, `chunk` símbolos por pedido). Devuelve {símbolo: {mcap_b (USD), price (moneda local), … _(línea 217)_
- `live_row_from_quote(q)` — make_quote() (core/providers/base) → fila del contrato /api/quotes/live: {close, prev, pct, live:&lt;precio numérico>, provider, as_of, … _(línea 313)_
- `live_cache_clear()` _(línea 354)_
- `fetch_quotes_live(tickers, registry=…, ttl=…, deadline=…)` — Cotizaciones EN VIVO de hasta LIVE_MAX_TICKERS tickers, en paralelo. `registry` inyectable (tests): objeto con get_quote(sym) → (quote, … _(línea 361)_

**Internas** (empiezan con `_`): `_fetch_quote_raw`, `_fx_to_usd`, `_yahoo_session`, `_live_pool`, `_age_seconds`, `_live_payload`

## Depende de

- [[core.config.py]] — importa `FINNHUB`
- [[core.http.py]] — importa `_safe_get`, `_safe_ticker`
- [[core.providers.market.py]] — importa `market_registry`

## Lo usan

- [[brokerage.service.py]] — lo importa
- [[core.company_data.py]] — lo importa
- [[core.live_caps.py]] — lo importa
- [[core.live_facts.py]] — lo importa
- [[core.options.py]] — lo importa
- [[core.portfolio_ai.py]] — lo importa
- [[core.portfolio_report.py]] — lo importa
- [[core.providers.market.py]] — lo importa
- [[core.risk_report.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- [[ontology.agents.py]] — lo importa
- [[research.context.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `get_exposure` → [[API herramientas MCP]]
- herramienta MCP `project_portfolio` → [[API herramientas MCP]]

_Además lo importan 7 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV LIVE_DEADLINE_S]]

## Pruebas que lo cubren

- [[tests.test_company_data.py]]
- [[tests.test_live_caps.py]]
- [[tests.test_mcp.py]]
- [[tests.test_overnight3_diag_bilingual.py]]
- [[tests.test_quotes_live.py]]
- [[tests.test_repair_prices.py]]
- [[tests.test_risk_easy.py]]
- [[tests.test_server_smoke.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-29 (noche) — TODO EN VIVO + AUDITORÍA DE DATOS FALSOS (sw v161)]]
- [[Sesión 2026-09-28 (b) — Estado en bolsa VERIFICADO (sw v142-143)]]
