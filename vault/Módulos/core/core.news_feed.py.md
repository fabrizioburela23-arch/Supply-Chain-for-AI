---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/news_feed.py"
lenguaje: "python"
lineas: 151
aliases: ["core/news_feed.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/news_feed.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 151 líneas · `core/news_feed.py`

## Para qué sirve

NOTICIAS DE TU CARTERA, con fecha y sin repetir lo viejo.

## API pública

- `portfolio_news(holdings, days=…, limit=…, lang=…, fetch=…)` — holdings: [{entity_id|id, label, symbol, weight_pct?}] → noticias ordenadas por relevancia. _(línea 91)_

**Internas** (empiezan con `_`): `_norm_title`, `_parse_dt`, `_company_news`

## Depende de

- [[core.config.py]] — importa `FINNHUB`
- [[core.http.py]] — importa `_safe_get`, `_safe_ticker`

## Lo usan

- [[core.portfolio_report.py]] — lo importa
- [[core.portfolio_reports_api.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_portfolio_reports.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-03 (b) — REPORTES DE CARTERA, PREGÚNTALE A TU CARTERA, NOTICIAS DE TU]]
