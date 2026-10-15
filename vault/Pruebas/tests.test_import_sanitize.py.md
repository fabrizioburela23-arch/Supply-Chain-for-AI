---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_import_sanitize.py"
lenguaje: "python"
lineas: 302
aliases: ["tests/test_import_sanitize.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_import_sanitize.py

> Prueba · capa [[Capa Pruebas]] · 302 líneas · `tests/test_import_sanitize.py`

## Qué prueba

lote L (2026-10-15): el saneador de FORMATO de las fichas khipus.company/1 (core/import_normalize.sanitize_record). Regla por regla; PURO (no toca la entrada), DETERMINISTA e IDEMPOTENTE (sanear dos veces = sanear una; registro vacío la segunda vez); NO INVENTA (todo valor de la salida está en la ficha original o en un cambio registrado); NINGÚN número cambia (los que sobreviven son idénticos); lo irreparable se quita —solo ese campo— y queda en el registro con su valor; una ficha se rechaza solo si su identidad queda inservible. Las mismas propiedades se comprueban sobre las 386 fichas REALES del lote (data/import/lotes/2026-10-15).

**17** funciones `test_…`.

## Cubre

- [[core.import_normalize.py]]
- [[ontology.company_schema.py]]

## Variables de entorno que fija o nombra

[[ENV KHIPU_SCHEDULER]]
