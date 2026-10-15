---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/prices_store.py"
lenguaje: "python"
lineas: 914
aliases: ["core/prices_store.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/prices_store.py

> Módulo · capa [[Capa Infraestructura]] · 914 líneas · `core/prices_store.py`

## Para qué sirve

LA MEMORIA DE LOS NÚMEROS (docs/BRECHAS_V2.md bloque 2; ARQUITECTURA_V2 §9.1, §20.1 #1-#3).

## API pública

- `req_interval_s()` — Pausa mínima entre pedidos a la fuente (PRICES_REQ_INTERVAL_S, por defecto 0,6 s). _(línea 59)_
- `daily_enabled()` _(línea 64)_
- `db_on()` _(línea 68)_
- `fetch_chart(symbol, rng=…, getter=…, now=…, years=…)` — → {'rows': [{date, open, high, low, close, adj_close, volume}], currency, tz, error}. La vela de la sesión que todavía NO cerró se descarta … _(línea 145)_
- `detect_adjustments(stored_eff, fetched, tol=…)` — Compara la ventana re-bajada con lo guardado (ya ajustado). → [(before_date, factor, evidence)]. Recorre las fechas comunes de la más nueva … _(línea 237)_
- `ingest_series(session, instrument_id, fetched, currency=…, source=…)` — Inserta las fechas nuevas y registra los ajustes detectados. Idempotente. → {inserted, adjustments}. _(línea 256)_
- `ingest_fx(session, ccy, fetched, source=…)` _(línea 288)_
- `load_series(session, instrument_id, start=…, source=…)` — [{date, close, adj, volume, currency}] ordenado, con los ajustes aplicados. _(línea 303)_
- `max_gap_days(dates)` — El mayor salto en días de calendario entre dos fechas seguidas (0 con menos de dos). _(línea 317)_
- `history(symbol, rng=…, today=…)` — DB primero: ({'YYYY-MM-DD': cierre ajustado}, moneda, meta{source, as_of, adjusted, n, from}) si la base cubre el rango pedido y está al … _(línea 335)_
- `volume_history(symbol, rng=…, today=…)` — ({'YYYY-MM-DD': volumen}, meta{source, as_of, n}) desde prices_eod si cubre el rango; None si no hay base, no cubre o el proveedor no trajo … _(línea 366)_
- `fx_history(ccy, rng=…, today=…)` — ({'YYYY-MM-DD': tasa ccy→USD}, meta) desde fx_daily si cubre el rango; None si no. _(línea 389)_
- `status()` — Resumen para el 🩺 y /api/prices/status (sin red). _(línea 413)_
- `snapshot_daily(session, run_date=…, broker=…)` — metrics_eod + positions_eod del día (una fila por clave; repetir es un no-op). → {metrics, positions}. _(línea 673)_
- `run_daily(now=…, getter=…, sleep=…, broker=…)` — Ingesta diaria (1 mes por instrumento, para detectar ajustes) + fotos del día. Bloqueante. _(línea 762)_
- `daily_tick(now=…, threaded=…)` — Tarea del reloj: si toca, lanza la corrida del día en su propio hilo (no bloquea al reloj). _(línea 787)_
- `backfill_state()` _(línea 825)_
- `start_backfill(principal, years=…, symbols=…, getter=…, sleep=…, threaded=…, interval=…)` — Arranca el relleno (decisión 'data.backfill' por el operador). RuntimeError si ya corre. _(línea 835)_
- `stop_backfill(principal)` — Pide detener el relleno (se puede reanudar: lo ya bajado se salta). Deja su decisión. _(línea 896)_

**Internas** (empiezan con `_`): `_env_float`, `_reads_paused`, `_read_failed`, `_now`, `_d`, `_f`, `_zone`, `_Pacer`, `_default_getter`, `_effective`, `_load_adjs`, `_covers`, `_targets`, `_phase_daily`, `_coverage`, `_one`, `_run`, `_last_close`, `_fx_on`, `_positions_rows`, `_daily_due`, `_record_finish`, `_reset_for_tests`

## Depende de

- [[brokerage.service.py]] — importa `service`
- [[core.company_data.py]] — importa `_get_json`
- [[core.decisions.py]] — importa `decisions`
- [[core.identity.py]] — importa `identity`
- [[core.instruments.py]] — importa `catalog_nodes`, `instruments`, `major_ccy`
- [[core.live_caps.py]] — importa `get_caps`
- [[core.risk_models.py]] — importa `adv_from_rows`
- [[core.world.py]] — importa `world`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[ontology.history_models.py]] — importa `FxDaily`, `MetricsEOD`, `PositionEOD`, `PriceAdjustment`, `PriceEOD`

## Lo usan

- [[core.prices_api.py]] — lo importa
- [[core.risk_report.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- [[research.context.py]] — lo importa
- [[scripts.calibrate_kernel.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `find_anomalies` → [[API herramientas MCP]]

_Además lo importan 8 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV PRICES_EOD]]
- [[ENV PRICES_REQ_INTERVAL_S]]

## Pruebas que lo cubren

- [[tests.test_live_universe.py]]
- [[tests.test_live_universe_db.py]]
- [[tests.test_lotek_fixer.py]]
- [[tests.test_prices_eod.py]]
- [[tests.test_risk_on_history.py]]
- [[tests.test_risk_robust.py]]
- [[tests.test_rsi_wilder.py]]
- [[tests.test_scenario_pnl.py]]
