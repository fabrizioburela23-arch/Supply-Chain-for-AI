---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/link_review.py"
lenguaje: "python"
lineas: 112
aliases: ["ontology/link_review.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/link_review.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 112 líneas · `ontology/link_review.py`

## Para qué sirve

COLA DE REVISIÓN de vínculos PROPUESTOS (2026-10-21, tras importar los lotes 2-4).

## API pública

- `priority(rel_type, props, deg_s, deg_t, flow=…)` _(línea 38)_
- `queue(session, limit=…, offset=…, q=…, lang=…)` — → {'total', 'items': [...], 'by_reason': {...}} de los vínculos propuestos vigentes, por prioridad. _(línea 55)_

**Internas** (empiezan con `_`): `_flow_types`

## Depende de

- [[ontology.models.py]] — importa `LinkRecord`, `ObjectRecord`
- [[ontology.vocabulary.py]] — importa `flow_relation_types`

## Lo usan

- [[ontology.api.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_link_review.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
