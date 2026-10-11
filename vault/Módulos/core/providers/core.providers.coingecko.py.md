---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/providers/coingecko.py"
lenguaje: "python"
lineas: 123
aliases: ["core/providers/coingecko.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/providers/coingecko.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 123 líneas · `core/providers/coingecko.py`

## Para qué sirve

adapter de cripto (CoinGecko API v3, tier gratuito).

## API pública

- `safe_coin_id(raw)` — Valida un id de CoinGecko ('bitcoin', 'matic-network'). None si inválido. _(línea 25)_
- `list_markets(per_page=…, page=…)` — Top de mercado cripto por capitalización. → (lista de CryptoAsset, error). _(línea 57)_
- `get_asset(coin_id)` — Detalle de una moneda. → (CryptoAsset completo, error). _(línea 72)_
- `get_history(coin_id, days=…)` — Serie de precios diarios. → ({'prices': [ [ts_ms, precio], …]}, error). _(línea 112)_

**Internas** (empiezan con `_`): `_key_param`, `_asset_from_market_row`

## Depende de

- [[core.http.py]] — importa `_safe_get`

## Lo usan

- [[core.providers.market.py]] — lo importa
- [[server.py]] — lo importa

## Variables de entorno que lee (solo nombres)

- [[ENV COINGECKO_KEY]]

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-07-12 — Etapa H — Feedback 7 - explicabilidad + regla bilingüe + cripto]]
