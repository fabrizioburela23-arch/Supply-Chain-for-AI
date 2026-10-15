---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_import_lote2_e2e.py"
lenguaje: "python"
lineas: 673
aliases: ["tests/test_import_lote2_e2e.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_import_lote2_e2e.py

> Prueba · capa [[Capa Pruebas]] · 673 líneas · `tests/test_import_lote2_e2e.py`

## Qué prueba

lote L (2026-10-15) DE PUNTA A PUNTA sobre Postgres, por la API REAL con PIN y con los MISMOS comandos de terminal que va a usar Fabrizio (`scripts/import_companies.py --plan … --server` y `--apply … --server`, con el cliente de pruebas de Flask en lugar de la red):

**23** funciones `test_…`.

## Cubre

- [[brokerage.models.py]]
- [[core.__init__.py]]
- [[core.entities.py]]
- [[core.http.py]]
- [[core.pin.py]]
- [[matrix.engine.py]]
- [[mcp_server.api.py]]
- [[mcp_server.models.py]]
- [[mcp_server.ops.py]]
- [[ontology.api.py]]
- [[ontology.bulk_import.py]]
- [[ontology.company_import.py]]
- [[ontology.db.py]]
- [[ontology.import_models.py]]
- [[ontology.models.py]]
- [[research.models.py]]
- [[scripts.import_companies.py]]
- [[scripts.migrate_v0_to_ontology.py]]
- [[server.py]]

## Rutas HTTP que llama

7 rutas, de los grupos: [[API MCP transporte y OAuth]], [[API mcp]], [[API ontology]]

## Variables de entorno que fija o nombra

[[ENV DATABASE_URL]], [[ENV KHIPU_SCHEDULER]], [[ENV SECRET_KEY]], [[ENV TRADE_PIN]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-15 — LOTE L - 386 EMPRESAS COMPLETAS + PANEL IMPORTAR + MAPA CON LAS DE LA]]
