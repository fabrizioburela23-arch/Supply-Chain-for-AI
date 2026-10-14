---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_import_normalize.py"
lenguaje: "python"
lineas: 90
aliases: ["tests/test_import_normalize.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_import_normalize.py

> Prueba · capa [[Capa Pruebas]] · 90 líneas · `tests/test_import_normalize.py`

## Qué prueba

EXPANSION_5K E2.2: las 136 grafías de país del catálogo mapean a ISO-2 (o a una región), MIC → sufijo de Yahoo, fechas parciales sin inventar el día (GENESIS sin start, nunca "ahora"), dinero en unidades + ISO 4217, ids de Khipus con el patrón del esquema.

**8** funciones `test_…`.

## Cubre

- [[core.import_normalize.py]]
- [[data.grafo_v0.json]]
- [[ontology.service.py]]
