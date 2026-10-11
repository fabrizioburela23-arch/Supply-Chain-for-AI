---
tipo: "modulo"
capa: "Investigación"
ruta: "research/health.py"
lenguaje: "python"
lineas: 202
aliases: ["research/health.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/health.py

> Módulo · capa [[Capa Investigación]] · 202 líneas · `research/health.py`

## Para qué sirve

"¿puedo investigar ahora?" en UNA foto (R6, misión de reparación).

## API pública

- `research_health(fresh=…, light=…)` — Dict serializable. Caché CACHE_S segundos (la llaman UI, MCP y /api/health). light=True (R11): SIN tocar la base — para /api/health … _(línea 160)_
- `health_brief()` — Resumen chico para /api/health: 100 % en memoria (sin base), nunca lanza. _(línea 190)_

**Internas** (empiezan con `_`): `_now_iso`, `_providers`, `_slots`, `_queue_and_budget`, `_ai_usage_limits`, `_scheduler`, `_outcomes`, `_routing`, `_last_errors`, `_hint`

## Depende de

- [[core.ai.py]] — importa `ai`
- [[core.ai_usage.py]] — importa `ai_usage`
- [[core.live_caps.py]] — importa `live_caps`
- [[core.scheduler.py]] — importa `scheduler`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[research.models.py]] — importa `ResearchJob`
- [[research.runner.py]] — importa `runner`

## Lo usan

- [[core.ops_check.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[research.api.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `get_research_health` → [[API herramientas MCP]]

_Además lo importan 3 pruebas (lista abajo)._

## Endpoints que llama

- `GET /api/research/health` → [[research.api.py]] ([[API research]])

## Variables de entorno que lee (solo nombres)

- [[ENV AI_ORDER]]
- [[ENV AI_ORDER_DEEP]]
- [[ENV AI_ORDER_FAST]]
- [[ENV RESEARCH_JOB_CONCURRENCY]]
- [[ENV RESEARCH_MODEL_DEFAULT]]
- [[ENV RESEARCH_PARALLEL]]

## Pruebas que lo cubren

- [[tests.test_overnight3_diag_bilingual.py]]
- [[tests.test_overnight_ai_routing.py]]
- [[tests.test_repair_research.py]]
