---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/governance_models.py"
lenguaje: "python"
lineas: 62
aliases: ["ontology/governance_models.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/governance_models.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 62 líneas · `ontology/governance_models.py`

## Para qué sirve

REGISTRO DE GOBERNANZA (docs/INFRA_OPERATIVA.md §5.1; paso 9 del plan).

## API pública

- clase `GovArtifact` _(línea 26)_
- clase `GovRelease` _(línea 46)_

## Depende de

- [[ontology.ledger_models.py]] — importa `XID8`, `txid_default`
- [[ontology.models.py]] — importa `Base`

## Lo usan

- [[ontology.models.py]] — lo importa

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
