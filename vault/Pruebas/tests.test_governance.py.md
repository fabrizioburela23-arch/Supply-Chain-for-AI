---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_governance.py"
lenguaje: "python"
lineas: 367
aliases: ["tests/test_governance.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_governance.py

> Prueba · capa [[Capa Pruebas]] · 367 líneas · `tests/test_governance.py`

## Qué prueba

INFRA_OPERATIVA paso 9: registro de gobernanza (core/governance, scripts/build_governance).

**20** funciones `test_…`.

## Cubre

- [[core.__init__.py]]
- [[core.decisions.py]]
- [[core.governance.py]]
- [[core.governance_api.py]]
- [[core.governance_lint.py]]
- [[core.identity.py]]
- [[core.pin.py]]
- [[matrix.engine.py]]
- [[matrix.tensor.py]]
- [[ontology.actions.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]
- [[ontology.vocabulary.py]]
- [[research.committee.py]]
- [[scripts.build_governance.py]]
- [[server.py]]

## Rutas HTTP que llama

4 rutas, de los grupos: [[API governance]], [[API vocabulary]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV GOV_RELEASE]], [[ENV TRADE_PIN]]
