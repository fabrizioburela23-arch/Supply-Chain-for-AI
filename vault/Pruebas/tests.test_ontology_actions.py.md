---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_ontology_actions.py"
lenguaje: "python"
lineas: 350
aliases: ["tests/test_ontology_actions.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_ontology_actions.py

> Prueba · capa [[Capa Pruebas]] · 350 líneas · `tests/test_ontology_actions.py`

## Qué prueba

Fase 2: catálogo de Acciones (escritura humana auditada). Requiere Postgres real (DATABASE_URL) — se auto-saltan si no está configurada, igual que test_ontology.py.

**17** funciones `test_…`.

## Cubre

- [[matrix.engine.py]]
- [[ontology.actions.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]]
