---
tipo: "modulo"
capa: "Investigación"
ruta: "research/api.py"
lenguaje: "python"
lineas: 322
aliases: ["research/api.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/api.py

> Módulo · capa [[Capa Investigación]] · 322 líneas · `research/api.py`

## Para qué sirve

blueprint /api/research/\* (Phase 2).

## API pública

- `agents()` _(línea 62)_
- `create()` _(línea 69)_
- `job(job_id)` _(línea 126)_
- `entity(entity_id)` _(línea 148)_
- `claim_why(claim_id)` — ¿POR QUÉ? claim → resumen de razonamiento → evidencia → fuentes → nodos afectados → contra-evidencia → ejecución que la produjo. _(línea 211)_
- `activity()` — Feed LIVE AGENT ACTIVITY: solo ejecuciones reales registradas. _(línea 255)_
- `health()` — R6: ¿puedo investigar ahora? Sin PIN, sin red, sin IA (caché 5 s). _(línea 274)_
- `budget()` _(línea 281)_
- `events()` — Evento → relevancia (entidades afectadas vía grafo) → agentes suscritos. _(línea 294)_

**Internas** (empiezan con `_`): `_unavailable`, `_iso`, `_claim_dict`, `_run_dict`, `_resolve`, `_coverage`, `_prefer_canonical`, `_entity_ids_for`

## Depende de

- [[core.ai.py]] — importa `_ai_configured`
- [[core.entities.py]] — importa `UMBRAL_BUSQUEDA`, `entity_ids_for`, `get_index`, `resolve`
- [[core.http.py]] — importa `rate_limit`
- [[ontology.db.py]] — importa `init_schema`, `ontology_available`, `session_scope`
- [[ontology.models.py]] — importa `ObjectRecord`
- [[ontology.provenance.py]] — importa `source_to_dict`
- [[research.agents.__init__.py]] — importa `AGENTS`
- [[research.errors.py]] — importa `run_hint`
- [[research.health.py]] — importa `research_health`
- [[research.models.py]] — importa `AgentRun`, `ClaimRelation`, `ResearchClaim`, `ResearchEvidence`, `ResearchJob`
- [[research.router.py]] — importa `dispatch_event`
- [[research.runner.py]] — importa `budget_exhausted`, `coverage_of`, `create_job`, `daily_budget`, `defer_job`, `execute_job_async`, `job_coverage`, `queue_position` …

## Lo usan

- [[server.py]] — lo importa

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/research/activity` | `activity` | [[engine.research.js]], 2 pruebas |
| `GET` | `/api/research/agents` | `agents` | — |
| `GET` | `/api/research/budget` | `budget` | — |
| `GET` | `/api/research/claims/<claim_id>` | `claim_why` | [[engine.research.js]], 2 pruebas |
| `GET` | `/api/research/entity/<entity_id>` | `entity` | [[engine.research.js]], 3 pruebas |
| `POST` | `/api/research/events` | `events` | — |
| `GET` | `/api/research/health` | `health` | [[research.health.py]], 1 prueba |
| `POST` | `/api/research/jobs` | `create` | [[engine.committee.js]], [[engine.pfcommittee.js]], [[engine.research.js]], 2 pruebas |
| `GET` | `/api/research/jobs/<job_id>` | `job` | [[engine.committee.js]], [[engine.research.js]], 1 prueba |

Grupos: [[API research]]

## Variables de entorno que lee (solo nombres)

- [[ENV RESEARCH_DAILY_BUDGET_USD]]

## Pruebas que lo cubren

- [[tests.test_overnight_ui_xray_research.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_research.py]]
