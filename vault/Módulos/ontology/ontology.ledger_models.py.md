---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/ledger_models.py"
lenguaje: "python"
lineas: 248
aliases: ["ontology/ledger_models.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/ledger_models.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 248 líneas · `ontology/ledger_models.py`

## Para qué sirve

el LIBRO DE DECISIONES (docs/INFRA_OPERATIVA.md §2.1; paso 6 del plan).

## API pública

- clase `DecisionBlob` _(línea 50)_
- clase `Decision` _(línea 63)_
- clase `DecisionRef` _(línea 113)_
- clase `DecisionOutcome` _(línea 132)_
- clase `DecisionViolation` _(línea 149)_
- clase `LedgerSeal` _(línea 165)_
- clase `LedgerMeta` _(línea 177)_
- clase `LedgerAnchor` — Ancla diaria (paso 7, §2.8): la cabeza de la cadena de sellos de ese día (UTC) en ese linaje, con el resultado de la verificación previa. … _(línea 186)_
- clase `AICall` — Paso 21 (§2.6, GV-11): UNA fila por pedido de texto a la IA (cascada de core/ai._ai_complete_raw). La escribe SOLO core/ai.py (vía … _(línea 202)_

**Internas** (empiezan con `_`): `_in`

## Depende de

- [[ontology.models.py]] — importa `Base`
- [[ontology.sqltypes.py]] — importa `XID8`, `txid_default`

## Lo usan

- [[core.ai_calls.py]] — lo importa
- [[core.decisions.py]] — lo importa
- [[core.ledger.py]] — lo importa
- [[ontology.models.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_cierre_defectos.py]]
