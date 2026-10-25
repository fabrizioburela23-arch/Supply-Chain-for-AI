---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_research_batch.py"
lenguaje: "python"
lineas: 144
aliases: ["tests/test_research_batch.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_research_batch.py

> Prueba · capa [[Capa Pruebas]] · 144 líneas · `tests/test_research_batch.py`

## Qué prueba

scripts/research_batch.py (2026-10-22): investiga empresas con la API de Claude y guarda SOLO fichas que pasan el mismo saneador + validador del importador; un turno pausado se retoma y una ficha inválida vuelve a la IA con sus errores una vez. Aquí con un cliente FALSO (sin red ni gasto).

**9** funciones `test_…`.

## Cubre

- [[scripts.research_batch.py]]

## Variables de entorno que fija o nombra

[[ENV SECRET_KEY]]
