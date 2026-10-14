---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_import_schema.py"
lenguaje: "python"
lineas: 123
aliases: ["tests/test_import_schema.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_import_schema.py

> Prueba · capa [[Capa Pruebas]] · 123 líneas · `tests/test_import_schema.py`

## Qué prueba

EXPANSION_5K E2.1: el espejo Pydantic (ontology/company_schema) ≡ el artefacto `ontology.import_schema` (= data/import/company.schema.json) en forma normalizada; los 13 negativos del plan se rechazan; un margen de -250 % se acepta; nulos explícitos y repetidos se rechazan como en JSON Schema.

**8** funciones `test_…`.

## Cubre

- [[core.governance.py]]
- [[ontology.company_schema.py]]
