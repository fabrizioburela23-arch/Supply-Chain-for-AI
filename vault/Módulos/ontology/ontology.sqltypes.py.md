---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/sqltypes.py"
lenguaje: "python"
lineas: 33
aliases: ["ontology/sqltypes.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/sqltypes.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 33 líneas · `ontology/sqltypes.py`

## Para qué sirve

tipos SQL compartidos por los modelos del libro y de gobernanza (módulo HOJA: no importa ningún modelo; lo importan ontology/ledger_models.py y ontology/governance_models.py).

## API pública

- clase `XID8` — xid8 (o bigint en Postgres < 13). Solo DDL: el código lo escribe por DEFAULT y lo lee como texto. _(línea 16)_
- clase `txid_default` — DEFAULT pg_current_xact_id() (o txid_current()) según la base. _(línea 25)_

**Internas** (empiezan con `_`): `_compile_txid_default`

## Depende de

- [[core.ledger_ddl.py]] — importa `ledger_ddl`

## Lo usan

- [[ontology.governance_models.py]] — lo importa
- [[ontology.ledger_models.py]] — lo importa

## Pruebas que lo cubren

- [[tests.test_cierre_defectos.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (h) — PASO 24 - REPETIR DECISIONES (replay), IMPLEMENTACIONES RETENIDAS]]
