---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/ledger.py"
lenguaje: "python"
lineas: 313
aliases: ["core/ledger.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/ledger.py

> Módulo · capa [[Capa Infraestructura]] · 313 líneas · `core/ledger.py`

## Para qué sirve

sellado y verificación del libro (docs/INFRA_OPERATIVA.md §2.8; paso 6 del plan).

## API pública

- `row_sha(j)` — sha de una fila leída con to_jsonb. Las columnas NULL se omiten: una columna NUEVA y nula (columna tardía, ALTER … ADD COLUMN sin DEFAULT) … _(línea 58)_
- `chain_hash(prev_hash, row_table, row_id, row_sha)` _(línea 66)_
- `on_schema_init(engine=…)` — init_schema: el esquema pudo re-crearse (tests, re-migración) → otro linaje; se relee/crea ahora. _(línea 75)_
- `lineage_id(engine=…)` — uuid del linaje de esta base (ledger_meta). Lo crea una vez, en su PROPIA transacción (no se pierde si la transacción del caller se … _(línea 86)_
- `seal(engine=…, batch=…)` — Una pasada del sellador. {'sealed': n, 'by_table': {...}, 'head': {seal_no, hash}, 'ms'} o {'skipped': 'locked'|'no_xid8'}. Idempotente; … _(línea 150)_
- `seal_job()` — Tarea del reloj (core/scheduler, `system:ledger_seal`): sella hasta 4 lotes seguidos si hay atraso. _(línea 202)_
- `verify(from_seal=…, limit=…, engine=…, max_broken=…)` — Recalcula la cadena desde `from_seal` y vuelve a leer cada fila sellada. {'ok', 'checked', 'from_seal', 'head': {seal_no, hash}, 'broken': … _(línea 240)_
- `status(engine=…)` — Resumen barato para el 🩺 y /api/ledger/status (sin cuerpos). _(línea 296)_

**Internas** (empiezan con `_`): `_canon_sha`, `_jsonb`, `_canonical_session`, `_existing`, `_head`, `_fetch_rows`

## Depende de

- [[core.decisions.py]] — importa `canonical`
- [[core.ledger_ddl.py]] — importa `ledger_ddl`
- [[ontology.db.py]] — importa `_get_engine`, `ontology_available`
- [[ontology.ledger_models.py]] — importa `LedgerSeal`

## Lo usan

- [[core.decisions.py]] — lo importa
- [[core.ledger_api.py]] — lo importa
- [[core.ledger_ddl.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_ledger_chain.py]]
- [[tests.test_ledger_core.py]]
- [[tests.test_ops_review_steps568.py]]
