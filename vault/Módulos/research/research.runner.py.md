---
tipo: "modulo"
capa: "Investigación"
ruta: "research/runner.py"
lenguaje: "python"
lineas: 1021
aliases: ["research/runner.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/runner.py

> Módulo · capa [[Capa Investigación]] · 1.021 líneas · `research/runner.py`

## Para qué sirve

ejecución de un ResearchJob (vertical slice → general).

## API pública

- `agent_parallelism()` _(línea 62)_
- `job_concurrency()` _(línea 87)_
- `research_queue_state()` — Foto de la cola (para /api/research/health y el 🩺): sin red, sin base. _(línea 91)_
- `queue_position(job_id)` — 1 = el siguiente en salir; None si no está en la cola. _(línea 110)_
- `agent_label(agent_type, lang=…)` _(línea 129)_
- `coverage_of(runs, requested)` — Cobertura PURA (sin base): runs = AgentRun (o algo con agent_type/status/ errors), requested = agentes pedidos. Un agente 'skipped' por … _(línea 134)_
- `job_coverage(session, job)` _(línea 194)_
- `missing_agents(session, job)` — Agentes que faltan en un job (según su cobertura guardada o sus runs). _(línea 199)_
- `daily_budget()` _(línea 208)_
- `budget_exhausted(session)` _(línea 212)_
- `next_resume_time(now=…)` — 00:05 UTC del día siguiente (el gasto diario se cuenta por día UTC). _(línea 216)_
- `defer_job(session, job, now=…)` — Marca el job 'deferred' con hora de reanudación. No crea runs ni gasta. _(línea 223)_
- `resume_deferred(session, now=…, max_jobs=…)` — Reanuda (→ 'queued') los jobs diferidos cuya hora llegó, SOLO los pedidos por personas (user/mcp/comité), máx. RESEARCH_RESUME_MAX (3) por … _(línea 261)_
- `resume_deferred_job()` — Tarea periódica (core/scheduler): reanuda y ENCOLA. Nunca lanza. _(línea 306)_
- `spent_today(session)` _(línea 331)_
- `create_job(session, entity_id, depth=…, agents=…, trigger=…, requested_by=…, force=…, only_missing=…)` — Crea (o REUTILIZA si hay uno igual reciente) un ResearchJob. No ejecuta. _(línea 354)_
- `retract_unsupported(session, entity_id)` — Retira (status='retracted') las claims ACTIVAS de la entidad cuyas cifras de dinero no aparecen en su propia evidencia guardada — p. ej. … _(línea 432)_
- `run_agent(session, job, agent_type, provider=…, fetchers=…, quotes=…)` — Ejecuta UN agente para el job (secuencial). Devuelve el AgentRun (siempre registrado). quotes: precios en vivo {símbolo: {...}} para la … _(línea 560)_
- `persist_result(session, job, run, agent, ctx, result, quotes=…)` — Escribe claims + evidencia. SOLO tablas research_\* (+ registrar Source citada, idempotente). Nunca toca hechos del grafo ni datos de … _(línea 570)_
- `baseline_quotes(entity_id, fetchers=…)` — Precio en vivo de la entidad y de SPY al crear las claims (auditoría de la foto de partida). Usa el fetcher 'profile' (caché 90 s; … _(línea 630)_
- `synthesize(session, job)` — Síntesis por horizonte: evidencia positiva, riesgos, preguntas abiertas y señales en conflicto. SIN comprar/vender/mantener (eso es Phase … _(línea 689)_
- `execute_job(session, job, provider_factory=…, fetchers=…, on_start=…, on_done=…)` — on_start(agent_type) / on_done(agent_type, run): avisos opcionales (la sala del comité los narra). _(línea 720)_
- `claim_job(session, job_id)` — R7: reclamo ATÓMICO del job ('queued' → 'running' en un solo UPDATE). Dos ejecutores (cola, recuperación, Pizarra, comité) no pueden correr … _(línea 747)_
- `execute_job_async(job_id)` — Encola el job (FIFO; RESEARCH_JOB_CONCURRENCY hilos). El cliente consulta /api/research/jobs/&lt;id> (queue_position) para ver el progreso … _(línea 924)_
- `recover_orphans_job()` — Tarea periódica (core/scheduler): recuperación de huérfanos. Nunca lanza. _(línea 987)_

**Internas** (empiezan con `_`): `_bg_slots`, `_agent_pool`, `_pool_submit`, `_parse_iso`, `_now`, `_cfg`, `_parse_dt`, `_ids_with_aliases`, `_completeness`, `_prepare_run`, `_agent_work`, `_agent_work_inner`, `_finish_run`, `_calibration_table`, `_calibration_for`, `_record_baseline`, `_register_source`, `_heartbeat`, `_execute_job`, `_run_job_id`, `_worker`, `_ensure_workers`, `_enqueue`, `_recover_orphans`, `_ensure_workers_quiet`, `_reset_workers`

## Depende de

- [[core.ai.py]] — importa `AI_INTERACTIVE_RESERVE`, `AI_MAX_CONCURRENCY`
- [[core.ai_usage.py]] — importa `ai_context`, `bind`
- [[core.entities.py]] — importa `entity_ids_for`, `get_index`
- [[core.logjson.py]] — importa `enabled`, `event`, `log_context`
- [[core.numbers.py]] — importa `evidence_numbers`, `unsupported_money`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[ontology.provenance.py]] — importa `register_source`
- [[research.agents.__init__.py]] — importa `AGENTS_BY_TYPE`
- [[research.confidence.py]] — importa `compute_confidence`
- [[research.context.py]] — importa `AGENT_NEEDS`, `ContextBuilder`
- [[research.contradictions.py]] — importa `detect_for`, `detect_semantic`
- [[research.errors.py]] — importa `run_hint`
- [[research.llm.py]] — importa `LLMError`, `RoutedProvider`, `estimate_cost`, `route_for`
- [[research.models.py]] — importa `AgentRun`, `ClaimRelation`, `DEPTHS`, `ResearchClaim`, `ResearchEvidence`, `ResearchJob`
- [[research.outcomes.py]] — importa `BENCH`, `calibration_detail`, `calibration_table`, `live_quotes`, `record_baseline`, `symbol_for`

## Lo usan

- [[mcp_server.tools.py]] — lo importa
- [[research.api.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[research.debate.py]] — lo importa
- [[research.health.py]] — lo importa
- [[research.router.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `get_research` → [[API herramientas MCP]]
- herramienta MCP `get_research_job` → [[API herramientas MCP]]
- herramienta MCP `run_research` → [[API herramientas MCP]]

_Además lo importan 6 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV RESEARCH_DAILY_BUDGET_USD]]
- [[ENV RESEARCH_DEDUPE_MINUTES]]
- [[ENV RESEARCH_HEARTBEAT_STALE_MIN]]
- [[ENV RESEARCH_JOB_CONCURRENCY]]
- [[ENV RESEARCH_MAX_AGENTS_PER_JOB]]
- [[ENV RESEARCH_PARALLEL]]
- [[ENV RESEARCH_RESUME_MAX]]
- [[ENV RESEARCH_STALE_MIN]]

## Pruebas que lo cubren

- [[tests.test_committee_os_narr.py]]
- [[tests.test_mcp.py]]
- [[tests.test_phase3.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_research.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-02 (noche) — ANÁLISIS MÁS PROFUNDO + CONCLUSIONES EN TODAS PARTES (sw v179)]]
