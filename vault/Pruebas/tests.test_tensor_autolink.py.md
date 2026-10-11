---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_tensor_autolink.py"
lenguaje: "python"
lineas: 61
aliases: ["tests/test_tensor_autolink.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_tensor_autolink.py

> Prueba · capa [[Capa Pruebas]] · 61 líneas · `tests/test_tensor_autolink.py`

## Qué prueba

Ontología nivel 2: al incorporar una empresa, sus proveedores/clientes probables quedan PROPUESTOS (confianza 0: no pesan en el riesgo hasta que una persona los confirma). Requiere Postgres.

**2** funciones `test_…`.

## Cubre

- [[matrix.engine.py]]
- [[matrix.tensor.py]]
- [[ontology.actions.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (ff) — ONTOLOGÍA NIVEL 2 - TENSORES + AUTO-CONEXIÓN (sw v241)]]
