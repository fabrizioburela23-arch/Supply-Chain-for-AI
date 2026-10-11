---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "core/options.py"
lenguaje: "python"
lineas: 214
aliases: ["core/options.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# core/options.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 214 líneas · `core/options.py`

## Para qué sirve

griegas de opciones y REPORTE VEGA (a.k.a. Kappa).

## API pública

- `bs(S, K, T, r, sigma, kind=…)` — Precio y griegas por 1 opción (no por contrato). vega: cambio de precio por +1 punto de volatilidad (σ + 0,01). theta: por día calendario. … _(línea 28)_
- `years_to(expiry, today=…)` _(línea 57)_
- `live_option(symbol, expiry, strike, kind, fetch=…)` — {spot, iv, bid, ask, last, open_interest, currency} del contrato, o {}. La IV viene de la cadena publicada por la bolsa (vía Yahoo). _(línea 83)_
- `chain_meta(symbol, expiry=…, fetch=…)` — Vencimientos y strikes disponibles (para los selectores de la UI). _(línea 105)_
- `risk_free_rate(fetch_hist=…)` — Rendimiento del T-bill 13 semanas (^IRX, en %) como decimal, o (0, False). _(línea 124)_
- `hist_vol(symbol, fetch_hist=…)` _(línea 136)_
- `vega_report(options, live=…, rate=…, hvol=…, today=…)` — options: [{symbol, kind, strike, expiry, contracts (+ largo / − corto), label?}] live(symbol, expiry, strike, kind) → dict · rate → (r, … _(línea 149)_

**Internas** (empiezan con `_`): `_ncdf`, `_npdf`, `_yahoo_json`

## Depende de

- [[core.http.py]] — importa `_safe_ticker`
- [[core.quotes.py]] — importa `_Y_SESS`, `_yahoo_session`
- [[core.risk_report.py]] — importa `RF_SYMBOL`, `_returns`, `_std`, `fetch_history`

## Lo usan

- [[mcp_server.tools.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `get_option_greeks` → [[API herramientas MCP]]

_Además lo importan 3 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_mcp.py]]
- [[tests.test_risk_easy.py]]
- [[tests.test_risk_options.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-29 (día) — REPORTE DE RIESGO - VaR + VEGA-KAPPA (sw v164)]]
