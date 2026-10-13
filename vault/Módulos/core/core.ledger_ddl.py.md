---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/ledger_ddl.py"
lenguaje: "python"
lineas: 201
aliases: ["core/ledger_ddl.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/ledger_ddl.py

> Módulo · capa [[Capa Infraestructura]] · 201 líneas · `core/ledger_ddl.py`

## Para qué sirve

DDL idempotente de los registros que SOLO crecen (docs/INFRA_OPERATIVA.md §2.1, §4.3).

## API pública

- `txid_expr()` — Expresión SQL del id de transacción actual según la base (xid8 desde Postgres 13). _(línea 59)_
- `safe_ddl(conn, sql, params=…)` — Un paso de DDL en su SAVEPOINT: si falla, se registra y la transacción exterior sigue viva. _(línea 68)_
- `detect_xid8(conn)` — Postgres ≥ 13 tiene xid8/pg_current_xact_id(). Se mira server_version_num (§7: Railway usa 16). _(línea 81)_
- `ensure_events(conn)` — DEFAULT de events.txid/seq (las columnas ya las creó _COLUMNAS_TARDIAS), índice parcial e índice por txid. Idempotente: solo toca lo que … _(línea 139)_
- `ensure_append_only(conn, tables=…)` — kh_append_only() + disparadores en cada tabla existente de `tables` (idempotente). _(línea 162)_
- `ensure_all(engine)` — Lo llama ontology.db.init_schema DESPUÉS de create_all y de las columnas tardías. Nunca lanza. Devuelve True si quedó todo (tablas del … _(línea 172)_
- `triggers_present(conn, tables=…)` — {tabla: bool} — para el 🩺 y las pruebas. _(línea 194)_

**Internas** (empiezan con `_`): `_txid_type`, `_tables_sql`, `_column_defaults`

## Depende de

_Nada interno._

## Lo usan

- [[brokerage.models.py]] — lo importa
- [[ontology.db.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_ops_events_append_only.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 — INFRAESTRUCTURA OPERATIVA, PASOS 1-4]]
