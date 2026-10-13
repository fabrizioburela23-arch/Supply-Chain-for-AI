---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "core/risk_report.py"
lenguaje: "python"
lineas: 553
aliases: ["core/risk_report.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# core/risk_report.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 553 líneas · `core/risk_report.py`

## Para qué sirve

REPORTE DE RIESGO DE CARTERA (VaR, estilo curso MIT).

## API pública

- `fetch_history(symbol, rng=…, getter=…)` — {fecha 'YYYY-MM-DD': precio ajustado} + moneda, o ({}, None). _(línea 38)_
- `history_meta(symbol, rng=…)` — {adjusted, tz, gmtoffset, n, source, as_of} de la última serie bajada (D1) o None. _(línea 90)_
- `fx_series(cur, rng=…, getter=…)` — L2-01 / L3-14: tipo de cambio DIARIO moneda→USD ({fecha: tasa}, meta) — base primero (fx_daily), si no la serie {CUR}USD=X de Yahoo. … _(línea 95)_
- `align_fx(prices, fx, max_gap_days=…)` — {fecha: tasa} para cada fecha de `prices`: la tasa de ese día o la última anterior (≤ max_gap_days; los feriados de cada mercado no … _(línea 117)_
- `kupiec_pof(x, n, p=…)` — Prueba de Kupiec (proportion of failures): x excepciones en n días con probabilidad p. Devuelve (LR, p-valor χ²(1)); sin scipy (erfc). _(línea 162)_
- `rolling_backtest(port, srt, conf=…)` — D3: backtest FUERA DE MUESTRA: el VaR de cada día se estima solo con los W días anteriores (W = max(60, min(125, n//2))) y se cuenta si la … _(línea 180)_
- `dimson_beta(y, b_lag, b_0, b_lead)` — L2-M1: beta de Dimson = suma de las pendientes de r_p,t sobre r_m,t−1, r_m,t y r_m,t+1 (OLS con constante). Las bolsas de Asia/Europa … _(línea 230)_
- `compute(histories, shares, fx, bench=…, horizon=…, rf=…, rf_source=…, nonsync=…)` — histories: {sym: {date: price}} · shares: {sym: n} · fx: {sym: moneda→USD} — un número (tasa de hoy) o {fecha: tasa} (L2-01/L3-14: la serie … _(línea 242)_
- `build_report(positions, horizon=…, rng=…, getter=…, fx_fn=…, max_positions=…)` — positions: [{symbol, shares, label?}] o [{symbol, usd, label?}] → reporte + lo excluido. _(línea 406)_

**Internas** (empiezan con `_`): `_returns`, `_mean`, `_std`, `_cov`, `_quantile`, `_fx_at`, `_solve`, `_histogram`

## Depende de

- [[core.company_data.py]] — importa `_get_json`
- [[core.http.py]] — importa `_safe_ticker`
- [[core.instruments.py]] — importa `major_ccy`, `nonsync`
- [[core.prices_store.py]] — importa `prices_store`
- [[core.quotes.py]] — importa `_fx_to_usd`

## Lo usan

- [[core.options.py]] — lo importa
- [[core.portfolio_advisor.py]] — lo importa
- [[core.portfolio_ai.py]] — lo importa
- [[core.portfolio_report.py]] — lo importa
- [[core.prices_api.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.outcomes.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `calculate_correlation` → [[API herramientas MCP]]
- herramienta MCP `get_history` → [[API herramientas MCP]]
- herramienta MCP `get_risk_report` → [[API herramientas MCP]]

_Además lo importan 5 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_mcp.py]]
- [[tests.test_repair_risk.py]]
- [[tests.test_review_batch_e.py]]
- [[tests.test_risk_easy.py]]
- [[tests.test_risk_on_history.py]]
- [[tests.test_risk_options.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (m) — EL COMITÉ ANALIZA TODAS LAS POSICIONES (sw v215)]]
- [[Sesión 2026-09-29 (día) — REPORTE DE RIESGO - VaR + VEGA-KAPPA (sw v164)]]
