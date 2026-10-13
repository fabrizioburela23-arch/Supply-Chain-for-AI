---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/checkpoints.py"
lenguaje: "python"
lineas: 212
aliases: ["ontology/checkpoints.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/checkpoints.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 212 líneas · `ontology/checkpoints.py`

## Para qué sirve

PUNTOS DE CONTROL del grafo (docs/INFRA_OPERATIVA.md §5.5; paso 26).

## API pública

- clase `GraphCheckpoint` _(línea 39)_
- `params()` _(línea 58)_
- `refresh_state(session, min_events=…)` — ¿Ya pasó el umbral? (una consulta; lo llama la tarea del reloj, nunca el camino del usuario). _(línea 89)_
- `build(session)` — Toma un punto de control AHORA (as_of_graph sin known_at, la vista de siempre). Devuelve sus metadatos. _(línea 98)_
- `lookup(session, as_of_dt, force=…)` — El grafo en `as_of_dt` desde el último punto de control, o None (→ pliegue de siempre). Exacto o nada. Desactivado (sin ninguna consulta) … _(línea 140)_
- `job(force=…)` — `system:graph_checkpoints` (cada hora): mira el umbral; por encima, toma uno si hay ≥ every eventos nuevos o el último tiene más de un día. _(línea 186)_
- `status()` _(línea 203)_

**Internas** (empiezan con `_`): `_event_stats`, `_graph_version`, `_lineage`, `_latest`, `_reset_for_tests`

## Depende de

- [[core.decisions.py]] — importa `canonical`
- [[core.governance.py]] — importa `governance`
- [[core.ledger.py]] — importa `ledger`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[ontology.models.py]] — importa `Base`
- [[ontology.service.py]] — importa `as_of_graph`

## Lo usan

- [[ontology.api.py]] — lo importa
- [[ontology.db.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_checkpoints.py]]
