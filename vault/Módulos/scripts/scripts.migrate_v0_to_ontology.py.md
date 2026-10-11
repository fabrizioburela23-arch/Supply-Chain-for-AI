---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "scripts/migrate_v0_to_ontology.py"
lenguaje: "python"
lineas: 493
aliases: ["scripts/migrate_v0_to_ontology.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# scripts/migrate_v0_to_ontology.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 493 líneas · `scripts/migrate_v0_to_ontology.py`

## Para qué sirve

Fase 1: migra data/grafo_v0.json (el snapshot congelado en Fase 0) a la ontología (Postgres, tabla events + vistas materializadas objects/links).

## API pública

- clase `RemigrateRefused` — La re-migración destructiva se negó (nada se borró). _(línea 81)_
- `main()` _(línea 94)_
- `check_reset_allowed(engine, confirm_db=…)` — Lanza RemigrateRefused si el borrado NO está autorizado. Devuelve el nombre de la base. `confirm_db`: nombre confirmado por el operador; … _(línea 166)_
- `claim_boot_remigration(engine, dbname, flag)` — Reserva la re-migración del ARRANQUE para este valor de REMIGRATE_ON_BOOT (una sola vez). Devuelve el id de la fila 'started'; lanza … _(línea 206)_
- `remigrate_flag_warning()` — Para /api/health o /api/diagnostics: si REMIGRATE_ON_BOOT sigue puesta, devuelve un aviso bilingüe (y si ese valor ya se ejecutó, cuándo). … _(línea 251)_
- `reset_graph_tables(engine, log=…)` — DROP SOLO de RESET_TABLES (en orden de FKs). No toca ninguna otra tabla. _(línea 279)_
- `run_migration(reset=…, dry_run=…, graph_path=…, log=…, confirm_db=…)` — Núcleo reutilizable de la migración v0 → ontología. Lo llama main() (CLI) y el hook REMIGRATE_ON_BOOT del server (para re-migrar producción … _(línea 288)_

**Internas** (empiezan con `_`): `_in_production`, `_local_reset_ok`, `_current_database`, `_protected_tables_with_rows`, `_ensure_remigrate_log`, `_finish_boot_remigration`, `_migrate_graph`, `_restore_factors_and_seats`

## Depende de

- [[core.pin.py]] — importa `in_production`
- [[ontology.db.py]] — importa `_get_engine`, `init_schema`, `ontology_available`, `session_scope`
- [[ontology.models.py]] — importa `Base`
- [[ontology.service.py]] — importa `GENESIS_SENTINEL`, `apply_event`
- [[data.grafo_v0.json]] — lo nombra por su ruta
- [[data.multicapa_factors_seats.json]] — lo nombra por su ruta

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV DATABASE_URL]]
- [[ENV RAILWAY_ENVIRONMENT]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV RAILWAY_ENVIRONMENT_NAME]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV RAILWAY_PROJECT_ID]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV REMIGRATE_ON_BOOT]]

## Pruebas que lo cubren

- [[tests.test_infra.py]]
- [[tests.test_matrix.py]]
- [[tests.test_ontology.py]]
- [[tests.test_repair_graph.py]]
