---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "scripts/calibrate_kernel.py"
lenguaje: "python"
lineas: 355
aliases: ["scripts/calibrate_kernel.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# scripts/calibrate_kernel.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 355 líneas · `scripts/calibrate_kernel.py`

## Para qué sirve

calibra κ (escenario → dinero) con episodios reales (BRECHAS L2-13 / PROP-16; batch I3).

## API pública

- `canonical(obj)` _(línea 65)_
- `sha256_of(obj)` _(línea 69)_
- `us_listed(sym)` — Solo cotizaciones en EE. UU. (acciones y ADR/OTC en USD): se comparan con SPY el mismo día y sin moneda. _(línea 77)_
- `episode_impacts(core, episode)` _(línea 83)_
- `mkt_map(data)` — {id: ticker principal (`mkt`)} de las empresas del grafo de lectura (catálogo/snapshot). _(línea 96)_
- `sample_for(core, impacts, seeds, tickers)` _(línea 102)_
- `prepare(kernel=…, episodes=…, snapshot=…)` _(línea 123)_
- `fetch(inputs, getter=…, use_db=…)` — Rellena inputs['prices'][símbolo] = {source, frequency, currency, closes{fecha: cierre ajustado}} solo con las fechas de las ventanas. … _(línea 167)_
- `fit_inputs(inputs, rules=…)` _(línea 213)_
- `build_artifact(inputs, inputs_path, semver, rules=…, parent=…)` _(línea 229)_
- `check()` — El artefacto más nuevo se reproduce desde su archivo de entradas (hash y ajuste idénticos). _(línea 278)_
- `main(argv=…)` _(línea 301)_

**Internas** (empiezan con `_`): `_now`, `_window_bounds`, `_slice`, `_covers_all`, `_latest_doc`

## Depende de

- [[core.__init__.py]] — importa `graph_core`, `impact`, `source`
- [[core.governance.py]] — importa `governance`
- [[core.prices_store.py]] — importa `prices_store`
- [[core.scenario_pnl.py]] — importa `close_on_or_before`, `scenario_pnl`
- [[ontology.db.py]] — importa `session_scope`

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
