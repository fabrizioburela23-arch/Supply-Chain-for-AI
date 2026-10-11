---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "core/risk_report.py"
lenguaje: "python"
lineas: 398
aliases: ["core/risk_report.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# core/risk_report.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 398 líneas · `core/risk_report.py`

## Para qué sirve

REPORTE DE RIESGO DE CARTERA (VaR, estilo curso MIT).

## API pública

- `fetch_history(symbol, rng=…, getter=…)` — {fecha 'YYYY-MM-DD': precio ajustado} + moneda, o ({}, None). _(línea 38)_
- `history_meta(symbol, rng=…)` — {adjusted, tz, gmtoffset, n} de la última serie bajada (D1) o None. _(línea 77)_
- `kupiec_pof(x, n, p=…)` — Prueba de Kupiec (proportion of failures): x excepciones en n días con probabilidad p. Devuelve (LR, p-valor χ²(1)); sin scipy (erfc). _(línea 112)_
- `rolling_backtest(port, srt, conf=…)` — D3: backtest FUERA DE MUESTRA: el VaR de cada día se estima solo con los W días anteriores (W = max(60, min(125, n//2))) y se cuenta si la … _(línea 130)_
- `compute(histories, shares, fx, bench=…, horizon=…, rf=…, rf_source=…)` — histories: {sym: {date: price}} · shares: {sym: n} · fx: {sym: moneda→USD}. bench: {date: price} del S&P 500 (opcional). rf: tasa libre de … _(línea 159)_
- `build_report(positions, horizon=…, rng=…, getter=…, fx_fn=…, max_positions=…)` — positions: [{symbol, shares, label?}] o [{symbol, usd, label?}] → reporte + lo excluido. _(línea 287)_

**Internas** (empiezan con `_`): `_returns`, `_mean`, `_std`, `_cov`, `_quantile`, `_histogram`

## Depende de

- [[core.company_data.py]] — importa `_get_json`
- [[core.http.py]] — importa `_safe_ticker`
- [[core.quotes.py]] — importa `_fx_to_usd`

## Lo usan

- [[core.options.py]] — lo importa
- [[core.portfolio_advisor.py]] — lo importa
- [[core.portfolio_ai.py]] — lo importa
- [[core.portfolio_report.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.outcomes.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `get_risk_report` → [[API herramientas MCP]]

_Además lo importan 4 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_mcp.py]]
- [[tests.test_repair_risk.py]]
- [[tests.test_risk_easy.py]]
- [[tests.test_risk_options.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (m) — EL COMITÉ ANALIZA TODAS LAS POSICIONES (sw v215)]]
- [[Sesión 2026-09-29 (día) — REPORTE DE RIESGO - VaR + VEGA-KAPPA (sw v164)]]
