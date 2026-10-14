---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_resolve_ids_impact_perf.py"
lenguaje: "python"
lineas: 195
aliases: ["tests/test_resolve_ids_impact_perf.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_resolve_ids_impact_perf.py

> Prueba · capa [[Capa Pruebas]] · 195 líneas · `tests/test_resolve_ids_impact_perf.py`

## Qué prueba

lote K (E1.1, pendiente del lote J): el bucle de orden/huella por fuente de core/hotviews/views/impact.py se vectorizó (un solo np.lexsort + conteos exactos) SIN cambiar nada de lo que publica: víctimas (ids, pct, salto) en el mismo orden, estadísticas, rankings by_sum/by_count, métricas y content_sha byte a byte.

**8** funciones `test_…`.

## Cubre

- [[core.__init__.py]]
- [[matrix.engine.py]]
- [[scripts.gen_synth_graph.py]]
