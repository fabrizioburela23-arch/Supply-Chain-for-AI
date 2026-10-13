---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "core/options.py"
lenguaje: "python"
lineas: 290
aliases: ["core/options.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# core/options.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 290 líneas · `core/options.py`

## Para qué sirve

griegas de opciones y REPORTE VEGA (a.k.a. Kappa).

## API pública

- `bs(S, K, T, r, sigma, kind=…, q=…)` — Precio y griegas por 1 opción (no por contrato), Black-Scholes-Merton con rendimiento de dividendo q. vega: cambio de precio por +1 punto … _(línea 33)_
- `years_to(expiry, today=…)` _(línea 64)_
- `live_option(symbol, expiry, strike, kind, fetch=…)` — {spot, iv, bid, ask, last, open_interest, currency} del contrato, o {}. La IV viene de la cadena publicada por la bolsa (vía Yahoo). _(línea 90)_
- `dividend_yield(quote)` — L2-10: rendimiento de dividendo ANUAL (decimal) que publica el proveedor para el subyacente, o None. Yahoo: trailingAnnualDividendYield … _(línea 113)_
- `chain_meta(symbol, expiry=…, fetch=…)` — Vencimientos y strikes disponibles (para los selectores de la UI). _(línea 127)_
- `risk_free_rate(fetch_hist=…)` — Rendimiento del T-bill 13 semanas (^IRX, en %) como decimal, o (0, False). _(línea 146)_
- `hist_vol(symbol, fetch_hist=…)` _(línea 158)_
- `vega_report(options, live=…, rate=…, hvol=…, today=…, fx_fn=…)` — options: [{symbol, kind, strike, expiry, contracts (+ largo / − corto), label?}] live(symbol, expiry, strike, kind) → dict · rate → (r, … _(línea 186)_

**Internas** (empiezan con `_`): `_ncdf`, `_npdf`, `_yahoo_json`, `_fx_rate`

## Depende de

- [[core.http.py]] — importa `_safe_ticker`
- [[core.instruments.py]] — importa `major_ccy`
- [[core.quotes.py]] — importa `_Y_SESS`, `_fx_to_usd`, `_yahoo_session`
- [[core.risk_report.py]] — importa `RF_SYMBOL`, `_returns`, `_std`, `fetch_history`

## Lo usan

- [[mcp_server.tools.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `get_option_greeks` → [[API herramientas MCP]]

_Además lo importan 4 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_mcp.py]]
- [[tests.test_options_greeks_totals.py]]
- [[tests.test_risk_easy.py]]
- [[tests.test_risk_options.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-29 (día) — REPORTE DE RIESGO - VaR + VEGA-KAPPA (sw v164)]]
