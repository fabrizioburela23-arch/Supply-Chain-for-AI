---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_scale_tensor_5k.py"
lenguaje: "python"
lineas: 108
aliases: ["tests/test_scale_tensor_5k.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_scale_tensor_5k.py

> Prueba · capa [[Capa Pruebas]] · 108 líneas · `tests/test_scale_tensor_5k.py`

## Qué prueba

metas de E1.2/E1.3 (docs/expansion/EXPANSION_5K.md §3) con 5.000 empresas sintéticas (scripts/gen_synth_graph.py). LENTA: solo corre con KH_SCALE=1 (fuera de la suite rápida, como test_scale_budget).

**1** funciones `test_…`.

## Cubre

- [[core.__init__.py]]
- [[core.live_fundamentals.py]]
- [[matrix.tensor.py]]
- [[ontology.db.py]]
- [[scripts.gen_synth_graph.py]]
