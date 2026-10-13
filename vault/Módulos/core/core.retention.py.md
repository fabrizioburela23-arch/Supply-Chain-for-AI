---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/retention.py"
lenguaje: "python"
lineas: 312
aliases: ["core/retention.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/retention.py

> Módulo · capa [[Capa Infraestructura]] · 312 líneas · `core/retention.py`

## Para qué sirve

PURGA POR RETENCIÓN del libro (docs/INFRA_OPERATIVA.md §2.7; paso 26; decisión D3).

## API pública

- `ensure(conn)` — Índices parciales de la purga (solo los que faltan: un CREATE INDEX toma candado aunque exista). _(línea 63)_
- `params()` — Parámetros del artefacto `ledger.retention` (sin artefacto: los de D3). _(línea 77)_
- `candidates(conn, days=…, limit=…)` — [(sha, kind, size)] purgables YA (lo mismo que la base aceptaría + lo citado en manifiestos sync o en cualquier decisión de la ventana). _(línea 152)_
- `purge(dry_run=…)` — Una corrida: purga los blobs vencidos y deja UNA decisión `retention.purge` (system:retention_purge) con los conteos y la lista de sha … _(línea 167)_
- `migrate_shadow_keys(limit=…)` — Reescribe las claves en texto plano de decision_shadow (anteriores al paso 20) como 'hmac0:&lt;hmac>' (HMAC del texto guardado, que ya venía … _(línea 218)_
- `daily_job(force=…)` — `system:retention_daily` (cada hora; una vez por día UTC): purga + limpieza de claves viejas de la sombra. _(línea 254)_
- `status()` — Para el 🩺: última corrida (de la base), pendientes y parámetros. _(línea 276)_

**Internas** (empiezan con `_`): `_cited_by_sync`, `_cited_recently`, `_ran_today`

## Depende de

- [[core.decisions.py]] — importa `decisions`
- [[core.governance.py]] — importa `governance`
- [[core.identity.py]] — importa `identity`
- [[core.ledger_ddl.py]] — importa `ledger_ddl`
- [[ontology.db.py]] — importa `_get_engine`, `ontology_available`, `session_scope`

## Lo usan

- [[core.ledger_ddl.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_retention_purge.py]]
- [[tests.test_review_batch_g.py]]
