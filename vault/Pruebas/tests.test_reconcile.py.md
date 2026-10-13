---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_reconcile.py"
lenguaje: "python"
lineas: 260
aliases: ["tests/test_reconcile.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_reconcile.py

> Prueba · capa [[Capa Pruebas]] · 260 líneas · `tests/test_reconcile.py`

## Qué prueba

G3 (misión de reparación 2026-10-04): reconciliar el catálogo (snapshot) con la ontología en Postgres SOLO con eventos.

**5** funciones `test_…`.

## Cubre

- [[core.http.py]]
- [[core.pin.py]]
- [[ontology.api.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.reconcile.py]]
- [[ontology.service.py]]
- [[server.py]]

## Rutas HTTP que llama

2 rutas, de los grupos: [[API ontology]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV TRADE_PIN]]
