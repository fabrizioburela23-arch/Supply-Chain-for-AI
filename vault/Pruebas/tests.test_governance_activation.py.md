---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_governance_activation.py"
lenguaje: "python"
lineas: 161
aliases: ["tests/test_governance_activation.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_governance_activation.py

> Prueba · capa [[Capa Pruebas]] · 161 líneas · `tests/test_governance_activation.py`

## Qué prueba

INFRA_OPERATIVA paso 12: activar kernel.params@2.0.0 con el PIN de Fabrizio (pieza mínima del paso 25) y deshacerlo.

**4** funciones `test_…`.

## Cubre

- [[core.__init__.py]]
- [[core.governance.py]]
- [[core.governance_api.py]]
- [[core.governance_flow.py]]
- [[core.governance_preview.py]]
- [[core.http.py]]
- [[core.identity.py]]
- [[core.pin.py]]
- [[matrix.engine.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]
- [[server.py]]

## Rutas HTTP que llama

2 rutas, de los grupos: [[API governance]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV TRADE_PIN]]
