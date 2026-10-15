---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/import_models.py"
lenguaje: "python"
lineas: 94
aliases: ["ontology/import_models.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/import_models.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 94 líneas · `ontology/import_models.py`

## Para qué sirve

tablas del importador de fichas khipus.company/1 (E2.3), APPEND-ONLY.

## API pública

- clase `ImportFile` _(línea 29)_
- clase `ImportRun` _(línea 41)_
- clase `ImportPendingLink` _(línea 59)_
- `ensure_tables(engine=…)` — Crea las tres tablas si faltan y les pone el disparador append-only. Idempotente; una vez por engine. _(línea 72)_

**Internas** (empiezan con `_`): `_reset_for_tests`

## Depende de

- [[core.ledger_ddl.py]] — importa `ledger_ddl`
- [[ontology.db.py]] — importa `_get_engine`
- [[ontology.models.py]] — importa `Base`

## Lo usan

- [[ontology.api.py]] — lo importa
- [[ontology.company_import.py]] — lo importa
- [[ontology.db.py]] — lo importa
- [[ontology.models.py]] — lo importa

_Además lo importan 5 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_catalog_api_pg.py]]
- [[tests.test_import_lote2_e2e.py]]
- [[tests.test_import_panel.py]]
- [[tests.test_import_roundtrip.py]]
- [[tests.test_live_universe_db.py]]
