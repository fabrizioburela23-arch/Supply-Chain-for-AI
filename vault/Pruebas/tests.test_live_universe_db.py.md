---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_live_universe_db.py"
lenguaje: "python"
lineas: 251
aliases: ["tests/test_live_universe_db.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_live_universe_db.py

> Prueba · capa [[Capa Pruebas]] · 251 líneas · `tests/test_live_universe_db.py`

## Qué prueba

lote L con Postgres: las 386 fichas completas aplicadas → el universo en vivo y la historia diaria las incluyen (por tandas, sin pasar el presupuesto de pedidos de hoy) y deshacer las saca.

**4** funciones `test_…`.

## Cubre

- [[brokerage.models.py]]
- [[core.__init__.py]]
- [[core.identity.py]]
- [[core.instruments.py]]
- [[core.live_caps.py]]
- [[core.prices_store.py]]
- [[core.quotes.py]]
- [[mcp_server.models.py]]
- [[ontology.company_import.py]]
- [[ontology.db.py]]
- [[ontology.import_models.py]]
- [[ontology.models.py]]
- [[research.models.py]]
- [[scripts.migrate_v0_to_ontology.py]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV KHIPU_SCHEDULER]], [[ENV SECRET_KEY]]
