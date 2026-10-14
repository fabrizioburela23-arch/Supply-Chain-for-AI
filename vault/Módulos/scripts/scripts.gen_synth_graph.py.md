---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "scripts/gen_synth_graph.py"
lenguaje: "python"
lineas: 174
aliases: ["scripts/gen_synth_graph.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# scripts/gen_synth_graph.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 174 líneas · `scripts/gen_synth_graph.py`

## Para qué sirve

grafo SINTÉTICO de N empresas para pruebas de escala (EXPANSION_5K E0.1).

## API pública

- `lift(g, n_target=…, seed=…, hub_bias=…, factors=…)` — (g2, factors2): snapshot y factores levantados a `n_target` empresas. No modifica `g` ni `factors`. `g2` tiene la forma del snapshot; … _(línea 43)_
- `synth_graphdata(n_target=…, seed=…, hub_bias=…)` — GraphData de core.hotviews.source del grafo levantado (sin base, sin tocar data/). _(línea 145)_
- `main(argv=…)` _(línea 152)_

**Internas** (empiezan con `_`): `_read_factors`, `_read_snapshot`

## Depende de

- [[core.__init__.py]] — importa `source`
- [[data.multicapa_factors_seats.json]] — lo nombra por su ruta

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_resolve_ids_impact_perf.py]]
- [[tests.test_scale_budget.py]]
- [[tests.test_scale_kernel.py]]
- [[tests.test_scale_search.py]]
- [[tests.test_scale_tensor_5k.py]]
