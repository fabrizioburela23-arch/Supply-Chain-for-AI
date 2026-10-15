---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_import_governance.py"
lenguaje: "python"
lineas: 57
aliases: ["tests/test_import_governance.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_import_governance.py

> Prueba · capa [[Capa Pruebas]] · 57 líneas · `tests/test_import_governance.py`

## Qué prueba

EXPANSION_5K E2.5: los artefactos del importador están en el registro de gobernanza (policy.import@1.1.0, ontology.import_schema@2.0.0 —lote L—, ledger.kinds@5.0.0 con ontology.import_rollback, ontology.shapes@7.0.0) y el código lee la política de ahí; nada cambia números del kernel (los dorados siguen iguales).

**5** funciones `test_…`.

## Cubre

- [[core.decisions.py]]
- [[core.governance.py]]
- [[ontology.bulk_import.py]]
- [[ontology.company_import.py]]
- [[scripts.build_governance.py]]
- [[scripts.build_impl_goldens.py]]

## Variables de entorno que fija o nombra

[[ENV KHIPU_SCHEDULER]]
