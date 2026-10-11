---
tipo: "modulo"
capa: "Comité"
ruta: "research/outcomes.py"
lenguaje: "python"
lineas: 716
aliases: ["research/outcomes.py"]
tags: ["capa/comite", "tipo/modulo"]
---

# research/outcomes.py

> Módulo · capa [[Capa Comité]] · 716 líneas · `research/outcomes.py`

## Para qué sirve

PHASE 3 · ¿ACERTARON LOS AGENTES? (aprendizaje)

## API pública

- `band_default()` — Banda de 'movimiento que cuenta' (fracción). Acepta 0.02 o 2 (= 2 %). _(línea 76)_
- `k_default()` _(línea 87)_
- `market_date(dt=…)` — Fecha de la sesión de EE.UU. a la que pertenece un instante. _(línea 103)_
- `nyse_holidays(y)` — Feriados de NYSE del año (reglas oficiales; Año Nuevo en sábado no se observa). _(línea 161)_
- `is_business_day(d)` _(línea 181)_
- `business_days_after(d, n)` — La fecha n días HÁBILES de NYSE después de d. _(línea 185)_
- `checkpoint_due(anchor, n, unit)` _(línea 195)_
- `build_checkpoints(horizon, anchor)` _(línea 199)_
- `symbol_for(entity_id)` — Ticker cotizado de la entidad (campo mkt del catálogo) o None. _(línea 208)_
- `na_reasons(horizon, stance, symbol)` — (motivo_es, motivo_en) por el que una claim NO se califica, o (None, None). _(línea 216)_
- `na_reason_for(horizon, stance, symbol)` _(línea 231)_
- `is_us_listing(symbol)` — ¿Ticker de EE.UU. (NVDA, BRK.B, MOG-A)? Los de otras bolsas llevan sufijo de Yahoo (2330.TW, 9984.T, BA.L…) o empiezan con dígito: cotizan … _(línea 238)_
- `live_quotes(symbols, profile_fn=…, timeout=…)` — {símbolo: {price, currency, source, as_of}} con el perfil en vivo. Acotado en tiempo (nunca frena la investigación más de `timeout` s). _(línea 245)_
- `record_baseline(session, claim, quotes=…, band=…, calibrated=…, source=…)` — Crea (una sola vez) la foto de partida de una claim. Devuelve la fila. _(línea 285)_
- `ensure_baselines(session, limit=…)` — Backfill: claims SIN foto de partida (p. ej. anteriores a Phase 3). _(línea 314)_
- `last_on_or_before(series, keys, d, max_lag=…)` _(línea 336)_
- `first_on_or_after(series, keys, d, max_lag=…)` — (fecha, precio) · 'gap' si el primer cierre está demasiado lejos · None si aún no existe. _(línea 346)_
- `default_price_fn(symbol, since)` — Cierres diarios AJUSTADOS reales (Yahoo) que cubren desde `since`. _(línea 357)_
- `judge(stance, excess, band)` _(línea 366)_
- `score_checkpoint(b, cp, get_series, today)` — Devuelve dict con el resultado, o None si todavía no se puede calificar. _(línea 383)_
- `session_in_progress(now)` — ¿La sesión de HOY todavía no cerró? (entonces la barra de hoy es un precio en curso). _(línea 440)_
- `evaluate_due(session, now=…, price_fn=…, limit=…)` — Califica los checkpoints vencidos con PRECIOS REALES. Idempotente. price_fn(símbolo, desde: date) -> {'YYYY-MM-DD': cierre ajustado} | None. _(línea 446)_
- `bucket_index(conf)` _(línea 545)_
- `bucket_label(i)` _(línea 550)_
- `stats(rows)` — rows: [(confianza, 1|0)] → n, aciertos, tasa, Brier y tramos de fiabilidad. _(línea 555)_
- `reliability(hits, n, k=…)` — Fiabilidad del agente con encogimiento hacia 0.5 (neutral sin historia). _(línea 571)_
- `track_record(session, agent_type=…)` — Historial por agente sobre checkpoints FINALES (+ señal temprana aparte). _(línea 577)_
- `invalidate_cache()` _(línea 618)_
- `calibration_table(session=…, force=…)` — {agent_type: {n, hits, buckets: [ [n, aciertos] × 5]}} (finales). Caché 10 min. _(línea 623)_
- `calibration_detail(agent_type, raw, session=…, table=…, k=…)` — Confianza calibrada con su cuenta (auditable). _(línea 639)_
- `calibrated_confidence(agent_type, raw, session=…, table=…, k=…)` — Número calibrado (0-1): (aciertos_tramo + k·cruda)/(n_tramo + k). _(línea 654)_
- `agent_reliability(agent_type, session=…, table=…, k=…)` _(línea 659)_
- `store_snapshot(session, now=…)` — Guarda la foto del historial (una fila por agente + global). _(línea 670)_
- `snapshots(session, agent_type=…, limit=…)` _(línea 688)_
- `outcomes_for_claim(session, claim_id)` _(línea 698)_
- `recent_outcomes(session, limit=…, agent_type=…)` _(línea 707)_

**Internas** (empiezan con `_`): `_now`, `_ny_tz`, `_ny_datetime`, `_easter`, `_nth_weekday`, `_last_weekday`, `_observed`, `_sorted_keys`, `_na`, `_snapshot_today`

## Depende de

- [[core.entities.py]] — importa `get_index`
- [[core.http.py]] — importa `_safe_ticker`
- [[core.risk_report.py]] — importa `fetch_history`
- [[research.context.py]] — importa `DEFAULT_FETCHERS`
- [[research.falsifiers.py]] — importa `apply_falsifiers`
- [[research.models.py]] — importa `CalibrationSnapshot`, `ClaimBaseline`, `ClaimOutcome`, `ResearchClaim`

## Lo usan

- [[core.agents_api.py]] — lo importa
- [[core.live_caps.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[research.runner.py]] — lo importa
- herramienta MCP `get_track_record` → [[API herramientas MCP]]

_Además lo importan 3 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV RESEARCH_CALIBRATION_K]]
- [[ENV RESEARCH_OUTCOME_BAND]]

## Pruebas que lo cubren

- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_phase3.py]]
- [[tests.test_repair_committee.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-30 — PHASE 3 + WORLD MONITOR + CORRETAJE + MCP + ENDURECIMIENTO (sw v170)]]
