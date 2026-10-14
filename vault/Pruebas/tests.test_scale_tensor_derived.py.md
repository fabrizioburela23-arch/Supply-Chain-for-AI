---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_scale_tensor_derived.py"
lenguaje: "python"
lineas: 120
aliases: ["tests/test_scale_tensor_derived.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_scale_tensor_derived.py

> Prueba · capa [[Capa Pruebas]] · 120 líneas · `tests/test_scale_tensor_derived.py`

## Qué prueba

E1.3 (docs/expansion/EXPANSION_5K.md): core/hotviews/derived guarda como MÁXIMO 2 generaciones CONTANDO la que se está construyendo (antes, mientras se armaba la 3.ª, seguían vivas las 2 anteriores: a 5.000 empresas eran 3 tensores densos de ~600 MB). Y la primera ficha de una generación no espera el NRS de todas.

**5** funciones `test_…`.

## Cubre

- [[core.__init__.py]]
- [[core.live_fundamentals.py]]
- [[ontology.db.py]]
