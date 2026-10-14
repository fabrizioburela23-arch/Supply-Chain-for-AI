---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_import_fast_path.py"
lenguaje: "python"
lineas: 166
aliases: ["tests/test_import_fast_path.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_import_fast_path.py

> Prueba · capa [[Capa Pruebas]] · 166 líneas · `tests/test_import_fast_path.py`

## Qué prueba

EXPANSION_5K E2.8: la escritura por bloques (ontology/bulk_import.write_events_fast) deja los MISMOS eventos que apply_event, campo a campo (tipo, extremos, payload con dedup_of, valid_from/valid_to reales, source_id, confidence, release_hash) y la misma materialización (objects/links); los vínculos llevan su fecha real (D-3: un vínculo con start 2021-07 nace en 2021-07; sin start, en GENESIS con valid_from_known false); 21.000 eventos entran en ≤ 30 s (lento: KH_SCALE=1). Requiere DATABASE_URL (base desechable, sin migrar el catálogo).

**4** funciones `test_…`.

## Cubre

- [[ontology.bulk_import.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV KHIPU_SCHEDULER]], [[ENV SECRET_KEY]]
