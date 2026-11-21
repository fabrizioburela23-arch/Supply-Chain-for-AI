---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_news_facts.py"
lenguaje: "python"
lineas: 192
aliases: ["tests/test_news_facts.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_news_facts.py

> Prueba · capa [[Capa Pruebas]] · 192 líneas · `tests/test_news_facts.py`

## Qué prueba

la ontología se actualiza sola: noticias → hechos (Lector) → curador → ciclo automático.

**11** funciones `test_…`.

## Cubre

- [[core.scheduler.py]]
- [[ontology.agents.py]]
- [[ontology.curation_loop.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.news_facts.py]]
- [[ontology.service.py]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV KHIPU_SCHEDULER]], [[ENV ONTOLOGY_AUTO]], [[ENV ONTOLOGY_NEWS_DAILY]], [[ENV ONTOLOGY_NEWS_FACTS]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
