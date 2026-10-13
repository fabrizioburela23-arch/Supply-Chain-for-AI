---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "brokerage/risk.py"
lenguaje: "python"
lineas: 651
aliases: ["brokerage/risk.py"]
tags: ["capa/dinero", "tipo/modulo"]
---

# brokerage/risk.py

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 651 líneas · `brokerage/risk.py`

## Para qué sirve

controles de riesgo PRE-orden por cliente.

## API pública

- `check_policy(mode=…)` — Política de controles por camino: 'standard' (👥 Clientes, MCP, comité) o 'house_today' (rutas clásicas de la casa con los límites de hoy). … _(línea 66)_
- `reduces_position(order, positions)` — True si `order` (por CANTIDAD) solo reduce o cierra una posición existente: del lado contrario a la posición (venta de una larga, compra de … _(línea 81)_
- `env_on(name, default=…)` _(línea 106)_
- `trading_enabled()` — Interruptor global del CORRETAJE. Por defecto ENCENDIDO (el papel debe funcionar); BROKERAGE_TRADING_ENABLED=off bloquea al instante toda … _(línea 110)_
- `live_env_enabled()` — Primer candado del dinero real (el segundo es client.live_enabled). _(línea 118)_
- `auto_approve_paper()` _(línea 123)_
- `effective_limits(profile, overrides=…, mandate=…)` — Límites numéricos efectivos = perfil + overrides del cliente. _(línea 127)_
- `effective_mandate(profile, mandate=…)` _(línea 145)_
- `asset_class(symbol)` _(línea 164)_
- `valid_symbol(symbol)` _(línea 168)_
- `trading_day_start(now=…)` — Inicio (UTC) del día de mercado de Nueva York que contiene `now`. _(línea 188)_
- `market_open_approx(now=…)` _(línea 196)_
- `run_checks(ctx)` — ctx: dict con client: {status, mode, live_enabled, connected, risk_profile, risk_limits, mandate, hwm_equity} order: {symbol, side, … _(línea 231)_
- `is_blocked(checks)` _(línea 529)_
- `failed(checks)` _(línea 533)_
- `order_facts(ctx, extra=…)` — Los hechos de una orden para el grafo foco (core/gates/focus.order_triples), con EXACTAMENTE la semántica de run_checks (mismas fórmulas, … _(línea 574)_

**Internas** (empiezan con `_`): `_ny_now`, `_c`, `_usd`, `_num`, `_min`, `_limits_and_mandate`, `_apply_shadow`, `_available`

## Depende de

- [[brokerage.alpaca.py]] — importa `is_crypto`
- [[core.governance.py]] — importa `governance`
- [[core.http.py]] — importa `_safe_ticker`
- [[core.ledger.py]] — importa `money_gate`

## Lo usan

- [[brokerage.service.py]] — lo importa
- [[core.impls.py]] — lo importa
- [[core.replay.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 6 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV BROKERAGE_AUTO_APPROVE_PAPER]]
- [[ENV BROKERAGE_LIVE_ENABLED]]
- [[ENV BROKERAGE_TRADING_ENABLED]]

## Pruebas que lo cubren

- [[tests.test_brokerage.py]]
- [[tests.test_gates_orders_parity.py]]
- [[tests.test_governance_seed_parity.py]]
- [[tests.test_impl_registry.py]]
- [[tests.test_ledger_anchor.py]]
- [[tests.test_order_single_path.py]]
