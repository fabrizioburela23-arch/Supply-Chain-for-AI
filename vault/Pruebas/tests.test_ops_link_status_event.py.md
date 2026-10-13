---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_ops_link_status_event.py"
lenguaje: "python"
lineas: 133
aliases: ["tests/test_ops_link_status_event.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_ops_link_status_event.py

> Prueba · capa [[Capa Pruebas]] · 133 líneas · `tests/test_ops_link_status_event.py`

## Qué prueba

INFRA_OPERATIVA paso 3: ConfirmarVinculo / RechazarVinculo emiten `LinkStatusChanged` en vez de mutar link.properties a mano (W5, GV-02).

**4** funciones `test_…`.

## Cubre

- [[matrix.engine.py]]
- [[ontology.actions.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]]
