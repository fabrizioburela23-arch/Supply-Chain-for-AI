---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_ledger_privacy.py"
lenguaje: "python"
lineas: 196
aliases: ["tests/test_ledger_privacy.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_ledger_privacy.py

> Prueba · capa [[Capa Pruebas]] · 196 líneas · `tests/test_ledger_privacy.py`

## Qué prueba

INFRA_OPERATIVA paso 6, §2.7: nunca texto personal en claro en el libro.

**7** funciones `test_…`.

## Cubre

- [[core.decide.py]]
- [[core.decisions.py]]
- [[core.http.py]]
- [[core.identity.py]]
- [[core.khipu_chat.py]]
- [[core.ledger_api.py]]
- [[core.pin.py]]
- [[ontology.db.py]]
- [[ontology.models.py]]

## Rutas HTTP que llama

2 rutas, de los grupos: [[API ledger]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV RAILWAY_ENVIRONMENT]], [[ENV RAILWAY_ENVIRONMENT_NAME]], [[ENV RAILWAY_PROJECT_ID]], [[ENV SECRET_KEY]], [[ENV TRADE_PIN]]
