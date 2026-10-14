---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/ledger_guard.py"
lenguaje: "python"
lineas: 451
aliases: ["core/ledger_guard.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/ledger_guard.py

> Módulo · capa [[Capa Infraestructura]] · 451 líneas · `core/ledger_guard.py`

## Para qué sirve

GUARDIA DE PROYECCIONES «sin decisión no hay cambio» (docs/INFRA_OPERATIVA.md §2.1; paso 22).

## API pública

- `ensure(conn)` — Tablas + función + disparadores (idempotente; lo llama core/ledger_ddl.ensure_all). Nunca lanza. _(línea 205)_
- `triggers_present(conn)` _(línea 223)_
- `policy_mode()` — El modo que pide el release VIGENTE (`policy.guard.mode`). Sin artefacto → 'warn'. _(línea 233)_
- `db_mode(conn)` _(línea 243)_
- `sync_mode(engine=…)` — Si la última fila de kh_guard_modes no es la del release vigente, agrega una (append-only). Nunca lanza. _(línea 251)_
- `register_release_listener()` _(línea 290)_
- `code_path(depth=…)` — 'brokerage/service.py:412 confirm_order < server.py:2501 trade_order' — los primeros marcos del repo. _(línea 306)_
- `install_listener(engine)` _(línea 386)_
- `on_schema_init(engine)` — Lo llama core/ledger_ddl.ensure_all después de crear todo: oyente + modo de la base + oyente de releases. _(línea 398)_
- `status(engine=…, days=…, fresh=…)` — {mode, mode_policy, ready, by_table: [{table, op, n}], total, paths: [...], since_days}. Caché 60 s. _(línea 409)_

**Internas** (empiezan con `_`): `_tables_sql`, `_on_release_change`, `_note`, `_scan`, `_after_cursor_execute`, `_on_checkin`, `_reset_for_tests`

## Depende de

- [[core.governance.py]] — importa `governance`
- [[core.ledger_ddl.py]] — importa `ledger_ddl`
- [[ontology.db.py]] — importa `_get_engine`, `ontology_available`
- [[ontology.db.py]] — lo nombra por su ruta

## Lo usan

- [[core.ledger_ddl.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV KH_GUARD_TRACE]]

## Pruebas que lo cubren

- [[tests.test_ledger_guard.py]]
- [[tests.test_review_batch_g.py]]
