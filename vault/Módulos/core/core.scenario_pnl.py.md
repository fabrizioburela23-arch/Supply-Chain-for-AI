---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "core/scenario_pnl.py"
lenguaje: "python"
lineas: 275
aliases: ["core/scenario_pnl.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# core/scenario_pnl.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 275 líneas · `core/scenario_pnl.py`

## Para qué sirve

ESCENARIO → DINERO (BRECHAS L2-13 / PROP-16; batch I3, 2026-10-13).

## API pública

- `calibration()` — (params, (ref, hash)) del kernel.calibration vigente, o (None, None) si este código/release no lo trae. _(línea 26)_
- `close_on_or_before(closes, day)` — (fecha, cierre) del último cierre en o antes de `day` ('YYYY-MM-DD'), o (None, None). _(línea 46)_
- `relative_drawdown(closes_i, closes_m, t0, t1)` — Peor caída de la empresa RELATIVA al mercado entre t0 (exclusivo, base = último cierre ≤ t0) y t1 (inclusive): min_d (P_i(d)/P_i(b)) / … _(línea 55)_
- `fit(points, rules=…)` — points [{episode, id, impact (0..1), y (≤0)}] → ajuste con efecto fijo por episodio: y = a_e − κ·impacto. Devuelve {status: … _(línea 92)_
- `series_problem(entry, t0, t1)` — Por qué una serie NO sirve para medir el episodio (o None): sin datos, sin ajustar (splits/dividendos), precio congelado (OTC sin … _(línea 161)_
- `points_from_inputs(inputs)` — El archivo de entradas (scripts/calibrate_kernel.py) → puntos {episode, id, symbol, impact, y, excluded}. Puro. `y` = None y `excluded` = … _(línea 178)_
- `cal_summary(cal, ref=…)` _(línea 216)_
- `translate(impacts, positions, cal=…, ref=…, kernel_semver=…)` — impacts {id: pct 0..100} (del kernel) + positions [{id, usd, symbol?}] → P&L estimado con banda o un estado honesto sin cifra. `cal`/`ref` … _(línea 227)_

**Internas** (empiezan con `_`): `_kernel_semver`, `_ols`, `_status`

## Depende de

- [[core.governance.py]] — importa `governance`

## Lo usan

- [[mcp_server.ops.py]] — lo importa
- [[scripts.calibrate_kernel.py]] — lo importa
- herramienta MCP `run_scenario` → [[API herramientas MCP]]

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_scenario_pnl.py]]
- [[tests.test_scenario_pnl_browser.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (k) — FASE 2+ LOTE I - rutas con decisión, CSP estricta, riesgo]]
