---
tipo: "modulo"
capa: "Investigación"
ruta: "research/confidence.py"
lenguaje: "python"
lineas: 111
aliases: ["research/confidence.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/confidence.py

> Módulo · capa [[Capa Investigación]] · 111 líneas · `research/confidence.py`

## Para qué sirve

confianza de una claim (metodología conf-v2).

## API pública

- `compute_confidence(support, counter, agent_certainty, completeness, now=…, statement=…)` — support/counter: listas de items del paquete de evidencia. statement (opcional): texto de la claim, para el tope de cifras sin fuente … _(línea 77)_

**Internas** (empiezan con `_`): `_parse`, `_recency`, `_is_external`, `_key`

## Depende de

- [[core.numbers.py]] — importa `money_mentions`

## Lo usan

- [[research.runner.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_repair_committee.py]]
- [[tests.test_research.py]]
