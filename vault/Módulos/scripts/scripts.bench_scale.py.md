---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "scripts/bench_scale.py"
lenguaje: "python"
lineas: 297
aliases: ["scripts/bench_scale.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# scripts/bench_scale.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 297 líneas · `scripts/bench_scale.py`

## Para qué sirve

banco de ESCALA de las vistas rápidas (EXPANSION_5K E0.1; port de exp5k/bench_hot.py).

## API pública

- `rss_mb()` _(línea 50)_
- `peak_mb()` _(línea 54)_
- `run(n=…, hub=…, seed=…, samples=…, structure=…, repeat=…)` — Mide y devuelve el dict del banco. `repeat` > 1: graph_core, impact, rho y pagerank se repiten y se informa el MÍNIMO (`ms_runs` trae todas … _(línea 79)_
- `main(argv=…)` _(línea 273)_

**Internas** (empiezan con `_`): `_proc`, `_pct`, `_timed`

## Depende de

- [[core.__init__.py]] — importa `card`, `graph`, `graph_core`, `hot`, `impact`, `registry`, `signals`, `source`
- [[core.context_engine.py]] — importa `context_engine`
- [[core.entities.py]] — importa `entities`
- [[core.world.py]] — importa `core.world`
- [[matrix.api.py]] — importa `_metrics_top`
- [[matrix.engine.py]] — importa `engine`
- [[matrix.tensor.py]] — importa `tensor`
- [[mcp_server.tools.py]] — importa `tools`

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Variables de entorno que lee (solo nombres)

- [[ENV DATABASE_URL]]
- [[ENV HOTVIEWS_LISTEN]]
- [[ENV KHIPU_SCHEDULER]]
- [[ENV MATRIX_ENGINE]]

## Pruebas que lo cubren

- [[tests.test_scale_budget.py]]
- [[tests.test_scale_hot_bench.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-14 (b) — LOTE J - SERVIDOR A 5.000 + CHAT PROGRESIVO (F3) + revisión — sw]]
