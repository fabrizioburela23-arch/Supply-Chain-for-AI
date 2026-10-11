---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_ingest_news.py"
lenguaje: "python"
lineas: 303
aliases: ["tests/test_ingest_news.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_ingest_news.py

> Prueba · capa [[Capa Pruebas]] · 303 líneas · `tests/test_ingest_news.py`

## Qué prueba

Phase 1 · M4: las noticias entran al grafo.

**12** funciones `test_…`.

## Cubre

- [[core.providers.base.py]]
- [[ontology.api.py]]
- [[ontology.db.py]]
- [[ontology.ingest_news.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]
- [[server.py]]

## Rutas HTTP que llama

2 rutas, de los grupos: [[API ontology]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV SECRET_KEY]]
