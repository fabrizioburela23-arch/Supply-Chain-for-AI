---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_ontology_agents.py"
lenguaje: "python"
lineas: 165
aliases: ["tests/test_ontology_agents.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_ontology_agents.py

> Prueba · capa [[Capa Pruebas]] · 165 líneas · `tests/test_ontology_agents.py`

## Qué prueba

Fase 3: agentes que proponen, cola de aprobación, brief matinal. Requiere Postgres real (DATABASE_URL).

**7** funciones `test_…`.

## Cubre

- [[ontology.actions.py]]
- [[ontology.agents.py]]
- [[ontology.api.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]
- [[server.py]]

## Rutas HTTP que llama

3 rutas, de los grupos: [[API ontology]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV SECRET_KEY]]
