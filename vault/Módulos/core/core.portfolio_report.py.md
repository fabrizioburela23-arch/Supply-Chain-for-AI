---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "core/portfolio_report.py"
lenguaje: "python"
lineas: 227
aliases: ["core/portfolio_report.py"]
tags: ["capa/dinero", "tipo/modulo"]
---

# core/portfolio_report.py

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 227 líneas · `core/portfolio_report.py`

## Para qué sirve

REPORTE DE CARTERA (a pedido, diario, semanal o mensual).

## API pública

- `build(positions, start_value=…, start_date=…, period=…, profile=…, cash_usd=…, lang=…, fetch=…, fx_fn=…, advisor=…, news=…)` — positions: [{id?, symbol, label, shares, cost_usd?}] (acciones actuales). _(línea 41)_
- `summarize(rep)` _(línea 172)_

**Internas** (empiezan con `_`): `_f`, `_histories`

## Depende de

- [[core.ai.py]] — importa `ai`
- [[core.ai_usage.py]] — importa `ai_context`
- [[core.news_feed.py]] — importa `news_feed`
- [[core.portfolio_advisor.py]] — importa `portfolio_advisor`
- [[core.quotes.py]] — importa `_fx_to_usd`
- [[core.risk_report.py]] — importa `fetch_history`

## Lo usan

- [[core.portfolio_reports_api.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_portfolio_reports.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-03 (b) — REPORTES DE CARTERA, PREGÚNTALE A TU CARTERA, NOTICIAS DE TU]]
