---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/company_data.py"
lenguaje: "python"
lineas: 1332
aliases: ["core/company_data.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/company_data.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 1.332 líneas · `core/company_data.py`

## Para qué sirve

estados financieros anuales y perfil EN VIVO de cualquier empresa cotizada del mundo (Dossier, 2026-09-28).

## API pública

- `yahoo_timeseries_to_annual(payload, fx=…, max_years=…)` — Payload de Yahoo fundamentals-timeseries → estructura normalizada (USD). Función PURA salvo `fx` (cur → tasa USD; por defecto core.quotes). _(línea 301)_
- `fmp_statements_to_annual(inc, cfs, bal, km, fx=…, max_years=…)` — Estados anuales de FMP (stable o v3) → estructura normalizada (USD). _(línea 361)_
- `av_reports_to_annual(inc, bal, cfs, fx=…, max_years=…)` — annualReports de Alpha Vantage (INCOME_STATEMENT, BALANCE_SHEET, CASH_FLOW) → estructura normalizada (USD). AV reporta capex POSITIVO. _(línea 414)_
- `get_annual_financials(ticker, fmp_key=…, av_key=…, use_cache=…)` — Series anuales normalizadas (USD) de una empresa cotizada. _(línea 706)_
- `to_findossier(fin, ticker)` — Estructura normalizada → respuesta de /api/findossier, con EXACTAMENTE las claves/unidades que consumen engine/fincard.js, cockpit.js, … _(línea 800)_
- `to_dossier(fin, ticker)` — Estructura normalizada → respuesta de /api/dossier con las claves y unidades que consume app.html `_dossierRenderPanels`: MILES DE MILLONES … _(línea 844)_
- `yahoo_quote_summary_to_profile(payload, fx=…, symbol=…)` — Payload de Yahoo quoteSummary → perfil en vivo (contrato). Márgenes, crecimiento y dividendo en %; precio/52 semanas/objetivo en moneda … _(línea 938)_
- `finnhub_to_profile(profile2, quote, metric=…, fx=…, symbol=…)` — Finnhub /stock/profile2 + /quote (+ /stock/metric opcional) → perfil. _(línea 1022)_
- `yahoo_chart_to_profile(payload, fx=…, symbol=…)` — Último recurso de precio: Yahoo v8/chart (no exige crumb). Solo precio, cierre previo y rango de 52 semanas si el meta lo trae. _(línea 1077)_
- `get_live_profile(ticker, finnhub_key=…, use_cache=…)` — Perfil EN VIVO de una empresa cotizada (cualquier bolsa). _(línea 1164)_
- `extract_valuation_mentions(articles, name)` — Pura (testeable): de artículos GDELT normalizados ({headline, url, source, datetime}) saca las valuaciones citadas en TITULARES que nombran … _(línea 1268)_
- `get_valuation_news(name)` — Menciones de valuación de una empresa en las noticias recientes (GDELT). Caché 30 min de éxitos, 5 min de fallos. Nunca lanza. _(línea 1304)_

**Internas** (empiezan con `_`): `_num`, `_str`, `_major`, `_usd_rate`, `_round`, `_pct`, `_now_iso`, `_has`, `_consecutive`, `_derive`, `_empty_fin`, `_assemble`, `_dominant`, `_Converter`, `_yahoo_series`, `_fmp_year`, `_fmp_index`, `_first`, `_av_index`, `_get_json`, `_yahoo_get`, `_sym`, `_fetch_fmp`, `_fetch_yahoo_fin`, `_fetch_av`, `_reason_pair`, `_classify`, `_explain`, `_score`, `_complete`, `_better`, `_cache_get`, `_cache_put`, `_lock_for`, `_clear_caches`, `_compute_annual`, `_blank_profile`, `_change_pct`, `_unix_iso`, `_merge_profile`, `_fetch_yahoo_summary`, `_fetch_finnhub_profile`, `_fetch_yahoo_chart`, `_compute_live`, `_to_float`

## Depende de

- [[core.config.py]] — importa `FINNHUB`
- [[core.quotes.py]] — importa `quotes`

## Lo usan

- [[core.live_facts.py]] — lo importa
- [[core.live_fundamentals.py]] — lo importa
- [[core.prices_store.py]] — lo importa
- [[core.risk_report.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.context.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 3 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV ALPHA_VANTAGE_KEY]]
- [[ENV AV_KEY]]
- [[ENV FMP_KEY]]

## Pruebas que lo cubren

- [[tests.test_company_data.py]]
- [[tests.test_risk_on_history.py]]
- [[tests.test_rsi_wilder.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-28 (d) — Valuación de PRIVADAS en vivo (sw v152)]]
- [[Sesión 2026-09-28 (c) — DOSSIER PARA TODAS LAS EMPRESAS + DATOS EN VIVO (sw v151)]]
