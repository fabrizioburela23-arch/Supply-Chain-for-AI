---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/ledger_ddl.py"
lenguaje: "python"
lineas: 308
aliases: ["core/ledger_ddl.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/ledger_ddl.py

> Módulo · capa [[Capa Infraestructura]] · 308 líneas · `core/ledger_ddl.py`

## Para qué sirve

DDL idempotente de los registros que SOLO crecen (docs/INFRA_OPERATIVA.md §2.1, §4.3).

## API pública

- `txid_expr()` — Expresión SQL del id de transacción actual según la base (xid8 desde Postgres 13). _(línea 69)_
- `safe_ddl(conn, sql, params=…)` — Un paso de DDL en su SAVEPOINT: si falla, se registra y la transacción exterior sigue viva. _(línea 78)_
- `detect_xid8(conn)` — Postgres ≥ 13 tiene xid8/pg_current_xact_id(). Se mira server_version_num (§7: Railway usa 16). _(línea 91)_
- `ensure_txid_seq(conn, table)` — DEFAULT de &lt;table>.txid/seq DESPUÉS de crear las columnas (las filas viejas quedan NULL = anteriores a la migración, nunca con un txid … _(línea 149)_
- `ensure_events(conn)` — DEFAULT de events.txid/seq (las columnas ya las creó _COLUMNAS_TARDIAS), índice parcial e índice por txid. Idempotente: solo toca lo que … _(línea 162)_
- `ensure_ledger(conn)` — Guardia de blobs, índices especiales del libro y DEFAULT de broker_audit.txid/seq. Idempotente. _(línea 235)_
- `blob_triggers_present(conn)` _(línea 255)_
- `ensure_append_only(conn, tables=…)` — kh_append_only() + disparadores en cada tabla existente de `tables` (idempotente). _(línea 263)_
- `ensure_all(engine)` — Lo llama ontology.db.init_schema DESPUÉS de create_all y de las columnas tardías. Nunca lanza. Devuelve True si quedó todo (tablas del … _(línea 273)_
- `triggers_present(conn, tables=…)` — {tabla: bool} — para el 🩺 y las pruebas. _(línea 301)_

**Internas** (empiezan con `_`): `_txid_type`, `_tables_sql`, `_column_defaults`

## Depende de

- [[core.ledger.py]] — importa `ledger`

## Lo usan

- [[brokerage.models.py]] — lo importa
- [[core.ledger.py]] — lo importa
- [[ontology.db.py]] — lo importa
- [[ontology.ledger_models.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_ops_events_append_only.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 — INFRAESTRUCTURA OPERATIVA, PASOS 1-4]]
