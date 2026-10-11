---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_repair_ontology_review.py"
lenguaje: "python"
lineas: 503
aliases: ["tests/test_repair_ontology_review.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_repair_ontology_review.py

> Prueba · capa [[Capa Pruebas]] · 503 líneas · `tests/test_repair_ontology_review.py`

## Qué prueba

G5: hallazgos de la revisión adversarial de G2/G3 (lentes "ontología" y "despliegue"). Cada test reproduce el escenario del hallazgo; sin los cambios de G5 fallan.

**23** funciones `test_…`.

## Cubre

- [[core.http.py]]
- [[core.pin.py]]
- [[ontology.actions.py]]
- [[ontology.api.py]]
- [[ontology.bulk_import.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.reconcile.py]]
- [[ontology.service.py]]
- [[server.py]]

## Rutas HTTP que llama

3 rutas, de los grupos: [[API ontology]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV TRADE_PIN]]
