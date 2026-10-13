---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/history_models.py"
lenguaje: "python"
lineas: 125
aliases: ["ontology/history_models.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/history_models.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 125 líneas · `ontology/history_models.py`

## Para qué sirve

LA MEMORIA DE LOS NÚMEROS (docs/BRECHAS_V2.md bloque 2: L3-01, L2-12, L3-14, L3-13).

## API pública

- clase `Instrument` _(línea 30)_
- clase `PriceEOD` _(línea 46)_
- clase `PriceAdjustment` _(línea 64)_
- clase `FxDaily` _(línea 77)_
- clase `MetricsEOD` _(línea 88)_
- clase `PositionEOD` _(línea 107)_

## Depende de

- [[ontology.models.py]] — importa `Base`

## Lo usan

- [[core.instruments.py]] — lo importa
- [[core.prices_store.py]] — lo importa
- [[ontology.models.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_cierre_defectos.py]]
