---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_hot_contract.py"
lenguaje: "python"
lineas: 196
aliases: ["tests/test_hot_contract.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_hot_contract.py

> Prueba · capa [[Capa Pruebas]] · 196 líneas · `tests/test_hot_contract.py`

## Qué prueba

INFRA_OPERATIVA paso 4 (§4.1, §4.6): el contrato de /api/hot/\* y de las rutas /api/matrix/\* que delegan.

**9** funciones `test_…`.

## Cubre

- [[core.__init__.py]]
- [[core.http.py]]
- [[matrix.api.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]
- [[server.py]]

## Rutas HTTP que llama

7 rutas, de los grupos: [[API health]], [[API matrix]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]]
