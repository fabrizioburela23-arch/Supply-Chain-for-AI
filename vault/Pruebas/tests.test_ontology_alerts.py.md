---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_ontology_alerts.py"
lenguaje: "python"
lineas: 90
aliases: ["tests/test_ontology_alerts.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_ontology_alerts.py

> Prueba · capa [[Capa Pruebas]] · 90 líneas · `tests/test_ontology_alerts.py`

## Qué prueba

Fase 4: alertas de precio/NRS/noticias. Requiere Postgres real (DATABASE_URL).

**5** funciones `test_…`.

## Cubre

- [[ontology.agents.py]]
- [[ontology.api.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]
- [[server.py]]

## Rutas HTTP que llama

3 rutas, de los grupos: [[API ontology]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV FINNHUB_KEY]], [[ENV SECRET_KEY]]
