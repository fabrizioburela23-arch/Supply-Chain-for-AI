---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/ops_check.py"
lenguaje: "python"
lineas: 252
aliases: ["core/ops_check.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/ops_check.py

> Módulo · capa [[Capa Infraestructura]] · 252 líneas · `core/ops_check.py`

## Para qué sirve

O1 (misión de reparación 2026-10-04): chequeo del sistema EN el servidor, guardado y consultable.

## API pública

- clase `OpsCheck` — Una corrida del chequeo (append-only). _(línea 40)_
- `run_checks(kind=…, persist=…)` _(línea 170)_
- `scheduled()` — Tarea del reloj (cada 5 min): corre una vez 5 min tras el arranque (humo del despliegue) y luego cada 24 h. Si no toca, no hace nada. _(línea 202)_
- `last_check(history=…)` _(línea 216)_
- `api_last_check()` _(línea 236)_

**Internas** (empiezan con `_`): `_now`, `_version`, `_check`, `_mcp_tool`, `_db`, `_snapshot`, `_ai`, `_scheduler`, `_world`, `_graph_drift`, `_register_manual_route`

## Depende de

- [[core.http.py]] — importa `rate_limit`
- [[core.pin.py]] — importa `require_operator`
- [[core.scheduler.py]] — importa `scheduler`
- [[core.world.py]] — importa `world`
- [[mcp_server.auth.py]] — importa `Principal`
- [[mcp_server.tools.py]] — importa `_snapshot`, `tools`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[ontology.models.py]] — importa `Base`
- [[ontology.reconcile.py]] — importa `reconcile`
- [[research.health.py]] — importa `research_health`
- [[sw.js]] — lo nombra por su ruta

## Lo usan

- [[ontology.db.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `POST` | `/api/ops/check` | `api_run_check` | 1 prueba |
| `GET` | `/api/ops/last_check` | `api_last_check` | 1 prueba |

Grupos: [[API ops]]

## Pruebas que lo cubren

- [[tests.test_repair_ops.py]]
