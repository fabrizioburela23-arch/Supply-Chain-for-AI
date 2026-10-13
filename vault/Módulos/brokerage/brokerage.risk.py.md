---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "brokerage/risk.py"
lenguaje: "python"
lineas: 449
aliases: ["brokerage/risk.py"]
tags: ["capa/dinero", "tipo/modulo"]
---

# brokerage/risk.py

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 449 líneas · `brokerage/risk.py`

## Para qué sirve

controles de riesgo PRE-orden por cliente.

## API pública

- `env_on(name, default=…)` _(línea 58)_
- `trading_enabled()` — Interruptor global del CORRETAJE. Por defecto ENCENDIDO (el papel debe funcionar); BROKERAGE_TRADING_ENABLED=off bloquea al instante toda … _(línea 62)_
- `live_env_enabled()` — Primer candado del dinero real (el segundo es client.live_enabled). _(línea 71)_
- `auto_approve_paper()` _(línea 76)_
- `effective_limits(profile, overrides=…, mandate=…)` — Límites numéricos efectivos = perfil + overrides del cliente. _(línea 80)_
- `effective_mandate(profile, mandate=…)` _(línea 98)_
- `asset_class(symbol)` _(línea 117)_
- `valid_symbol(symbol)` _(línea 121)_
- `trading_day_start(now=…)` — Inicio (UTC) del día de mercado de Nueva York que contiene `now`. _(línea 141)_
- `market_open_approx(now=…)` _(línea 149)_
- `run_checks(ctx)` — ctx: dict con client: {status, mode, live_enabled, connected, risk_profile, risk_limits, mandate, hwm_equity} order: {symbol, side, … _(línea 184)_
- `is_blocked(checks)` _(línea 444)_
- `failed(checks)` _(línea 448)_

**Internas** (empiezan con `_`): `_ny_now`, `_c`, `_usd`, `_num`, `_min`

## Depende de

- [[brokerage.alpaca.py]] — importa `is_crypto`
- [[core.governance.py]] — importa `governance`
- [[core.http.py]] — importa `_safe_ticker`
- [[core.ledger.py]] — importa `money_gate`

## Lo usan

- [[brokerage.service.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 3 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV BROKERAGE_AUTO_APPROVE_PAPER]]
- [[ENV BROKERAGE_LIVE_ENABLED]]
- [[ENV BROKERAGE_TRADING_ENABLED]]

## Pruebas que lo cubren

- [[tests.test_brokerage.py]]
- [[tests.test_governance_seed_parity.py]]
- [[tests.test_ledger_anchor.py]]
