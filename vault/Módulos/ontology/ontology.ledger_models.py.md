---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/ledger_models.py"
lenguaje: "python"
lineas: 271
aliases: ["ontology/ledger_models.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/ledger_models.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 271 líneas · `ontology/ledger_models.py`

## Para qué sirve

el LIBRO DE DECISIONES (docs/INFRA_OPERATIVA.md §2.1; paso 6 del plan).

## API pública

- clase `XID8` — xid8 (o bigint en Postgres < 13). Solo DDL: el código lo escribe por DEFAULT y lo lee como texto. _(línea 36)_
- clase `txid_default` — DEFAULT pg_current_xact_id() (o txid_current()) según la base. _(línea 45)_
- clase `DecisionBlob` _(línea 73)_
- clase `Decision` _(línea 86)_
- clase `DecisionRef` _(línea 136)_
- clase `DecisionOutcome` _(línea 155)_
- clase `DecisionViolation` _(línea 172)_
- clase `LedgerSeal` _(línea 188)_
- clase `LedgerMeta` _(línea 200)_
- clase `LedgerAnchor` — Ancla diaria (paso 7, §2.8): la cabeza de la cadena de sellos de ese día (UTC) en ese linaje, con el resultado de la verificación previa. … _(línea 209)_
- clase `AICall` — Paso 21 (§2.6, GV-11): UNA fila por pedido de texto a la IA (cascada de core/ai._ai_complete_raw). La escribe SOLO core/ai.py (vía … _(línea 225)_

**Internas** (empiezan con `_`): `_compile_txid_default`, `_in`

## Depende de

- [[core.ledger_ddl.py]] — importa `ledger_ddl`
- [[ontology.models.py]] — importa `Base`

## Lo usan

- [[core.ai_calls.py]] — lo importa
- [[core.decisions.py]] — lo importa
- [[core.ledger.py]] — lo importa
- [[ontology.governance_models.py]] — lo importa
- [[ontology.models.py]] — lo importa

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
