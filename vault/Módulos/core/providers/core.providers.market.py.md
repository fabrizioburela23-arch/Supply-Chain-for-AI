---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/providers/market.py"
lenguaje: "python"
lineas: 159
aliases: ["core/providers/market.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/providers/market.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 159 líneas · `core/providers/market.py`

## Para qué sirve

Phase 1 · M3: adapters de datos de mercado.

## API pública

- clase `FinnhubProvider` — Finnhub: cotización de EE.UU. en tiempo casi real. Requiere key. _(línea 21)_
- clase `YahooProvider` — Yahoo Finance: cualquier bolsa del mundo, SIN key. Es el que cubre los símbolos con sufijo (688825.SS, 7203.T, 005930.KS…) y convierte a … _(línea 72)_
- clase `CoinGeckoProvider` — Cripto. Era el ÚNICO adapter que existía; ahora cumple el mismo contrato que los de acciones, así que la cascada es uniforme. _(línea 105)_
- `market_registry()` — Cascada de acciones: Finnhub primero (más fresco y con timestamp real), Yahoo después (cubre el resto del mundo y no necesita key). _(línea 143)_
- `crypto_registry()` _(línea 155)_

**Internas** (empiezan con `_`): `_utcnow`

## Depende de

- [[core.config.py]] — importa `FINNHUB`
- [[core.http.py]] — importa `_safe_ticker`
- [[core.providers.base.py]] — importa `MarketDataProvider`, `ProviderRegistry`, `ProviderStatus`, `make_quote`
- [[core.providers.coingecko.py]] — importa `coingecko`
- [[core.quotes.py]] — importa `_fetch_quote_raw`, `fetch_quote_intl`, `finnhub_circuit_state`, `is_intl`

## Lo usan

- [[core.quotes.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 3 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV COINGECKO_KEY]]

## Pruebas que lo cubren

- [[tests.test_providers.py]]
- [[tests.test_quotes_live.py]]
- [[tests.test_repair_prices.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-22 al 24 — PHASE 1 Live Investment Graph COMPLETA + velocidad + 3D temporal]]
