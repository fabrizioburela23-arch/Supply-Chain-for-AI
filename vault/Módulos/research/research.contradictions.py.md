---
tipo: "modulo"
capa: "Investigación"
ruta: "research/contradictions.py"
lenguaje: "python"
lineas: 143
aliases: ["research/contradictions.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/contradictions.py

> Módulo · capa [[Capa Investigación]] · 143 líneas · `research/contradictions.py`

## Para qué sirve

detección INICIAL de tensiones entre claims.

## API pública

- `related_topics(topic)` — El tema y los de su familia (si tiene). _(línea 29)_
- `detect_for(session, claim)` — Crea relaciones para UNA claim nueva. Devuelve las creadas. _(línea 37)_
- `semantic_pairs(session, job_id)` _(línea 92)_
- `detect_semantic(session, job_id, provider)` — Revisa con IA los pares candidatos del job. Devuelve relaciones creadas. Un fallo del modelo en un par NO rompe nada: ese par se omite. _(línea 120)_

## Depende de

- [[research.models.py]] — importa `ClaimRelation`, `ResearchClaim`

## Lo usan

- [[research.runner.py]] — lo importa

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
