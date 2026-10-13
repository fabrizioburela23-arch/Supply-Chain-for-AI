---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/bitemporal.py"
lenguaje: "python"
lineas: 356
aliases: ["ontology/bitemporal.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/bitemporal.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 356 líneas · `ontology/bitemporal.py`

## Para qué sirve

G(t, κ): el grafo vigente en la fecha t TAL COMO SE CONOCÍA en κ (INFRA_OPERATIVA §5.5).

## API pública

- clase `KnownAtError` — known_at inválido (texto bilingüe en .es / .en). _(línea 34)_
- clase `Known` _(línea 43)_
- `parse_known(raw)` — Texto/número → ('gv', int) | ('ts', datetime) | None (sin κ: 'now', vacío). Lanza KnownAtError. _(línea 79)_
- `capabilities(session)` — ¿La base tiene kh_tx_versions y events.txid? (to_regclass/information_schema: nunca falla). _(línea 109)_
- `current_version(session)` _(línea 133)_
- `resolve(session, raw)` — known_at (texto, número, datetime o Known) → Known | None (None = sin κ: el camino de siempre). _(línea 139)_
- `orphan_mark(session, ts)` — recorded_at del último evento ESTRUCTURAL y ECONÓMICO con txid pero SIN versión (huérfano) registrado hasta `ts` (None si no hay). Los … _(línea 178)_
- `now_known(session)` — κ = ahora (la versión actual): G(t, ahora) debe ser EXACTAMENTE el as_of de siempre (paridad). _(línea 206)_
- `visible(known)` — Cláusula SQLAlchemy sobre `events` (FROM events, sin alias): ¿el evento era conocido en κ? _(línea 213)_
- `props_at(session, ids=…, t=…, known=…, types=…)` — {id: {id, type, label, properties, valid_from, updated_from, retired, merged_into}} en (t, κ). _(línea 230)_
- `object_props_dict(o)` — props_at → dict serializable (fechas ISO, centinela marcado como en el resto de la API). _(línea 283)_
- `economic_ids_at(session, t=…, known=…)` — Nodos económicos que EXISTEN en (t, κ), en orden de id (DT-M2: existencia de nodos en el tiempo). _(línea 297)_
- `delta_theta(session, from_dt, to_dt, known=…, limit=…)` — Δθ (L3-07): qué PROPIEDADES de nodos económicos/factores cambiaron entre dos fechas de validez, y qué nodos aparecieron. Solo mira los … _(línea 303)_
- `scale_note(session)` — ¿Ya conviene object_versions? (umbral documentado; nunca se construye sola). _(línea 345)_

**Internas** (empiezan con `_`): `_utcnow`, `_as_utc`, `_has_seq`

## Depende de

- [[core.__init__.py]] — importa `signals`
- [[core.ledger_ddl.py]] — importa `ledger_ddl`
- [[ontology.models.py]] — importa `Event`
- [[ontology.service.py]] — importa `is_genesis`
- [[ontology.vocabulary.py]] — importa `vocabulary`

## Lo usan

- [[matrix.engine.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[ontology.service.py]] — lo importa
- [[ontology.timeline.py]] — lo importa
- herramienta MCP `get_ontology_object` → [[API herramientas MCP]]

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_bitemporal.py]]
- [[tests.test_bitemporal_review.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (f) — PASOS 22, 23, 25, 26 Y 11]]
