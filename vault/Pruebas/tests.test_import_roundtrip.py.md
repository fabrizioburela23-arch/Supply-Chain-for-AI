---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_import_roundtrip.py"
lenguaje: "python"
lineas: 388
aliases: ["tests/test_import_roundtrip.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_import_roundtrip.py

> Prueba · capa [[Capa Pruebas]] · 388 líneas · `tests/test_import_roundtrip.py`

## Qué prueba

EXPANSION_5K E2.3/E2.4/E2.8 con Postgres: plan → aplicar → deshacer sobre una muestra real de 50 fichas del lote 1 + una ficha sintética con vínculos (fechado 2021-07, sin fecha → GENESIS, rumor → propuesta, contraparte desconocida → pendiente, terminado → valid_to).

**12** funciones `test_…`.

## Cubre

- [[brokerage.models.py]]
- [[core.__init__.py]]
- [[core.decisions.py]]
- [[core.http.py]]
- [[core.identity.py]]
- [[core.pin.py]]
- [[mcp_server.models.py]]
- [[ontology.api.py]]
- [[ontology.bulk_import.py]]
- [[ontology.company_import.py]]
- [[ontology.db.py]]
- [[ontology.import_models.py]]
- [[ontology.models.py]]
- [[ontology.service.py]]
- [[research.models.py]]
- [[scripts.migrate_v0_to_ontology.py]]
- [[server.py]]

## Rutas HTTP que llama

5 rutas, de los grupos: [[API ontology]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV KHIPU_SCHEDULER]], [[ENV SECRET_KEY]], [[ENV TRADE_PIN]]
