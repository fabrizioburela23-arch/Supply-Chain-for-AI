---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_ontology.py"
lenguaje: "python"
lineas: 295
aliases: ["tests/test_ontology.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_ontology.py

> Prueba · capa [[Capa Pruebas]] · 295 líneas · `tests/test_ontology.py`

## Qué prueba

Fase 1: esquema de eventos, materialización, time-travel (as_of) y diff. Requiere una Postgres real accesible vía DATABASE_URL (se skippean automáticamente si no está configurada — no bloquean CI sin base de datos, igual que los tests que necesitan API keys).

**12** funciones `test_…`.

## Cubre

- [[data.grafo_v0.json]]
- [[data.multicapa_factors_seats.json]]
- [[ontology.actions.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]
- [[scripts.export_graph_v0.js]]
- [[scripts.migrate_v0_to_ontology.py]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]]
