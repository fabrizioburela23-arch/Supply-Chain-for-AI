---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/ledger_models.py"
lenguaje: "python"
lineas: 208
aliases: ["ontology/ledger_models.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/ledger_models.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 208 líneas · `ontology/ledger_models.py`

## Para qué sirve

el LIBRO DE DECISIONES (docs/INFRA_OPERATIVA.md §2.1; paso 6 del plan).

## API pública

- clase `XID8` — xid8 (o bigint en Postgres < 13). Solo DDL: el código lo escribe por DEFAULT y lo lee como texto. _(línea 34)_
- clase `txid_default` — DEFAULT pg_current_xact_id() (o txid_current()) según la base. _(línea 43)_
- clase `DecisionBlob` _(línea 71)_
- clase `Decision` _(línea 84)_
- clase `DecisionRef` _(línea 134)_
- clase `DecisionOutcome` _(línea 153)_
- clase `DecisionViolation` _(línea 170)_
- clase `LedgerSeal` _(línea 186)_
- clase `LedgerMeta` _(línea 198)_

**Internas** (empiezan con `_`): `_compile_txid_default`, `_in`

## Depende de

- [[core.ledger_ddl.py]] — importa `ledger_ddl`
- [[ontology.models.py]] — importa `Base`

## Lo usan

- [[core.decisions.py]] — lo importa
- [[core.ledger.py]] — lo importa
- [[ontology.models.py]] — lo importa

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
