---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_link_review.py"
lenguaje: "python"
lineas: 53
aliases: ["tests/test_link_review.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_link_review.py

> Prueba · capa [[Capa Pruebas]] · 53 líneas · `tests/test_link_review.py`

## Qué prueba

Cola de revisión de vínculos PROPUESTOS (2026-10-21): ontology/link_review ordena por importancia (flujo > socio, criticidad, confianza declarada, grado de los extremos); confirmar/rechazar = la Acción auditada de siempre. El panel 📥 (engine/importer.js) la muestra con ✓ / ✕ (PIN).

**4** funciones `test_…`.

## Cubre

- [[engine.importer.js]]
- [[ontology.api.py]]
- [[ontology.db.py]]
- [[ontology.link_review.py]]
- [[server.py]]

## Rutas HTTP que llama

1 rutas, de los grupos: [[API ontology]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV SECRET_KEY]]
