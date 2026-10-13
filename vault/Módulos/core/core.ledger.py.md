---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/ledger.py"
lenguaje: "python"
lineas: 683
aliases: ["core/ledger.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/ledger.py

> Módulo · capa [[Capa Infraestructura]] · 683 líneas · `core/ledger.py`

## Para qué sirve

sellado y verificación del libro (docs/INFRA_OPERATIVA.md §2.8; paso 6 del plan).

## API pública

- `row_sha(j)` — sha de una fila leída con to_jsonb. Las columnas NULL se omiten: una columna NUEVA y nula (columna tardía, ALTER … ADD COLUMN sin DEFAULT) … _(línea 74)_
- `chain_hash(prev_hash, row_table, row_id, row_sha)` _(línea 82)_
- `on_schema_init(engine=…)` — init_schema: el esquema pudo re-crearse (tests, re-migración) → otro linaje; se relee/crea ahora. _(línea 91)_
- `lineage_id(engine=…)` — uuid del linaje de esta base (ledger_meta). Lo crea una vez, en su PROPIA transacción (no se pierde si la transacción del caller se … _(línea 102)_
- `seal(engine=…, batch=…)` — Una pasada del sellador. {'sealed': n, 'by_table': {...}, 'head': {seal_no, hash}, 'ms'} o {'skipped': 'locked'|'no_xid8'}. Idempotente; … _(línea 167)_
- `seal_job()` — Tarea del reloj (core/scheduler, `system:ledger_seal`): sella hasta 4 lotes seguidos si hay atraso. _(línea 219)_
- `verify(from_seal=…, limit=…, engine=…, max_broken=…, record_break=…)` — Recalcula la cadena desde `from_seal` y vuelve a leer cada fila sellada. {'ok', 'checked', 'from_seal', 'head': {seal_no, hash}, 'broken': … _(línea 257)_
- `status(engine=…)` — Resumen barato para el 🩺 y /api/ledger/status (sin cuerpos). _(línea 331)_
- `break_key(seal_no, reason, cur_hash=…)` — Clave de una ruptura: sello + motivo + hash ACTUAL de la fila (o del eslabón). Un segundo cambio en una fila ya rota (y reconocida) da otra … _(línea 387)_
- `record_chain_break(verify_out, engine=…)` — Una verificación con sellos rotos → decisión `ledger.chain_break` (sync, sesión propia). Si TODOS sus sellos rotos ya están en una ruptura … _(línea 454)_
- `chain_state(engine=…, fresh=…)` — {'broken', 'break_id', 'since', 'broken_count', 'acked': [...], 'error'}. Rota = hay una `ledger.chain_break` sin un `ledger.chain_ack` que … _(línea 486)_
- `money_gate(engine=…)` — ¿Puede moverse DINERO REAL? (ok, es, en). Cadena rota sin reconocer → no. Sin poder leer el estado con la base configurada → no (falla … _(línea 509)_
- `chain_ack(session, principal, note=…, break_id=…)` — Reconoce la ruptura vigente (o `break_id`) — decisión `ledger.chain_ack` con parent_id = la ruptura. Exige una PERSONA con PIN. Devuelve … _(línea 530)_
- `latest_anchor(engine=…)` _(línea 559)_
- `anchor(engine=…, force_verify=…)` — Ancla del día (UTC de la base): sella lo pendiente, verifica la cadena (completa hasta FULL_VERIFY_MAX sellos; si no, desde la última … _(línea 571)_
- `anchor_job()` — Tarea del reloj (`system:ledger_anchor`, cada hora): ancla del día si aún no existe + linaje. _(línea 608)_
- `check_lineage(engine=…)` — ¿Hubo una restauración? (a) el cluster (pg_control_system().system_identifier) cambió respecto del linaje vigente, o (b) el contador de … _(línea 623)_

**Internas** (empiezan con `_`): `_canon_sha`, `_jsonb`, `_canonical_session`, `_existing`, `_head`, `_fetch_rows`, `_chain_summary`, `_engine`, `_broken_key`, `_anchor_mismatches`, `_known_break_keys`, `_is_known`, `_invalidate_chain`, `_decision_rows`

## Depende de

- [[core.decisions.py]] — importa `canonical`, `decisions`
- [[core.identity.py]] — importa `identity`
- [[core.ledger_ddl.py]] — importa `ledger_ddl`
- [[ontology.db.py]] — importa `_get_engine`, `ontology_available`, `session_scope`
- [[ontology.ledger_models.py]] — importa `LedgerSeal`

## Lo usan

- [[brokerage.risk.py]] — lo importa
- [[brokerage.service.py]] — lo importa
- [[core.decisions.py]] — lo importa
- [[core.ledger_api.py]] — lo importa
- [[core.ledger_ddl.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 5 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_ledger_anchor.py]]
- [[tests.test_ledger_chain.py]]
- [[tests.test_ledger_core.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_review_infra_c.py]]
