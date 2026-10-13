---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/decision_sites.py"
lenguaje: "python"
lineas: 714
aliases: ["core/decision_sites.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/decision_sites.py

> Módulo · capa [[Capa Infraestructura]] · 714 líneas · `core/decision_sites.py`

## Para qué sirve

decisiones del COMITÉ, la INVESTIGACIÓN, las PROPUESTAS y las ALERTAS (docs/INFRA_OPERATIVA.md §2.5; pasos 18 y 19 del plan).

## API pública

- `principal(task, declared=…)` — QUIÉN: el principal del hilo (identity.use) o de la petición; sin contexto, `system:&lt;task>`. _(línea 43)_
- `clean(v)` — JSON seguro para el libro: NaN/inf → None, fechas → ISO, recursivo (la forma canónica rechaza NaN). _(línea 58)_
- `claim_hash(c)` — Huella de un claim tal como se VIO (texto, confianza, método conf-v2, estado) — §2.6. _(línea 78)_
- `evidence_hash(e)` — Huella de una evidencia E#: su referencia (URL/fuente) y su fecha. _(línea 87)_
- `cite_policy(ctx, aid)` _(línea 94)_
- `find_decisions(session, ref_kind, ref_ids, kinds)` — {ref_id: decision_id más reciente} de las decisiones `kinds` que tienen (ref_kind, ref_id) como EFECTO. Dentro de un SAVEPOINT: sin libro … _(línea 103)_
- `find_decision(session, ref_kind, ref_id, kinds)` _(línea 123)_
- `after_response(fn, what)` — Corre `fn()` FUERA del camino del usuario (la cola del libro de core/decisions si existe; si no, un hilo). Nunca lanza; sin base no hace … _(línea 127)_
- `flush()` — Pruebas: espera lo encolado por after_response. _(línea 154)_
- `policy_change(session, policy, before, after, subject=…, task=…, declared=…, p=…)` — policy.change (sync, misma sesión) con el valor ANTERIOR y el nuevo. Sin cambio real → no escribe nada. _(línea 172)_
- `memo_facts(memo, now=…)` — Hechos del memo para la puerta G5 (core/gates/focus.memo_triples). Los topes salen del release vigente. _(línea 188)_
- `gate_memo(memo, session=…, now=…)` — Puerta G5 (SOMBRA): el reporte queda en la decisión en curso (committee.run o approval.\*). Nunca lanza. _(línea 224)_
- `committee_run(session, memo, claims, package=…, rels=…, decision_id=…)` — committee.run (sync) al guardar el memo 'proposed', en la MISMA transacción: si la ficha no se escribe, el memo tampoco (el hilo lo marca … _(línea 234)_
- `reserve_id()` — decision_id reservado ANTES del trabajo de IA (comité, analistas): las filas de ai_calls de ese trabajo lo llevan (core/ai_calls.attribute, … _(línea 304)_
- `ai_attributed(decision_id)` — Atribuye las llamadas de IA del bloque (y de los hilos que lo hereden con core/ai_usage.bind) a la decisión reservada. Devuelve la lista de … _(línea 312)_
- `record_reserved_failure(kind, decision_id, who, subject=…, error=…)` — El trabajo con IA atribuida a `decision_id` falló ANTES de abrir su decisión: se escribe esa decisión como 'failed' (sesión autónoma) para … _(línea 328)_
- `approval(session, verdict, target_kind, target_ref, parent_id=…, note=…, actor=…, task=…, subject=…)` — approval.grant | approval.deny que ENVUELVE el efecto (la previsualización del memo, la Acción de la propuesta): lo que se escriba dentro … _(línea 363)_
- `memo_approval(session, memo_id, verdict, actor=…, note=…)` _(línea 390)_
- `portfolio_advice(analysis, positions=…, profile=…, owner_hash=…, lang=…, saved_id=…, actor=…)` — committee.portfolio_advice DESPUÉS de responder (consejo, no escribe nada del dominio): la ficha se arma en la cola del libro. Retención … _(línea 397)_
- `research_job(session, job)` — research.job (sync) al CREAR un pedido nuevo (los reutilizados no escriben nada): quién, disparador, analistas. _(línea 439)_
- `research_job_closed(session, job, coverage=…)` — Cierre del pedido (sync): hija del research.job de creación. done/partial → executed, failed, deferred → noop. _(línea 457)_
- `research_run(session, job, run, agent, decision_id=…)` — research.run (sync) de UN analista, en la MISMA transacción que sus claims y su evidencia. Lo que pase dentro (claim.status por claims … _(línea 486)_
- `claim_status(session, claim_ids, to_status, from_status=…, reason=…, notes=…, parent_id=…, task=…)` — claim.status (sync): la transición de estado de uno o varios claims (superseded, retracted, falsified), con la regla/métrica/valor de cada … _(línea 525)_
- `claim_evals(session, rows, source=…)` — decision_outcomes 'claim_eval' sobre el research.run que CREÓ cada claim (dedup claim:checkpoint). Es un resultado POSTERIOR (no un … _(línea 545)_
- `agent_principal(agent_name)` — Los agentes de la ontología trabajan para el Radar (registro único): agent:radar@1 + su nombre de etiqueta. _(línea 582)_
- `proposal_create(session, agent_name, proposal)` — proposal.create (sync): envuelve la creación de la propuesta (la puerta G-PROP queda en ESTA ficha). El caller llama `done(pa)` tras añadir … _(línea 592)_
- `proposal_auto_apply(session, p, min_conf=…)` — proposal.auto_apply (sync, system:auto_apply): cita policy.auto_apply (D6 sin respuesta: 1.0.0, el comportamiento de hoy). La … _(línea 616)_
- `proposal_parent(session, pid)` _(línea 636)_
- `owner_hash(owner)` _(línea 641)_
- `alert_rule(session, alert, op, actor=…)` — alert.rule (sync): alta o baja de una regla. El dueño (texto libre) SOLO como hash con clave. _(línea 646)_
- `alert_fire_due(alert_id, prev_fired_at, now)` — ¿Toca escribir alert.fire para esta alerta que disparó AHORA? Límite de RITMO (revisión paso 19): como mucho una ficha cada FIRE_GAP_S … _(línea 667)_
- `alert_fires(items)` — alert.fire (async, fuera del camino del usuario): una ficha por alerta disparada (system:alerts) con valor, umbral y detalle. `items`: … _(línea 690)_

**Internas** (empiezan con `_`): `_sha`, `_changed_keys`, `_Approval`, `_run_principal`, `_close_run`, `_as_dt`

## Depende de

- [[core.__init__.py]] — importa `core.gates`, `focus`
- [[core.ai_calls.py]] — importa `ai_calls`
- [[core.decisions.py]] — importa `decisions`, `sha256_hex`
- [[core.governance.py]] — importa `governance`
- [[core.identity.py]] — importa `identity`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[research.committee.py]] — importa `PROMPT_VERSION`, `_ttl_hours`
- [[research.models.py]] — importa `ResearchClaim`, `ResearchEvidence`

## Lo usan

- [[brokerage.service.py]] — lo importa
- [[core.ai_usage.py]] — lo importa
- [[core.impls.py]] — lo importa
- [[core.replay.py]] — lo importa
- [[ontology.agents.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[research.falsifiers.py]] — lo importa
- [[research.outcomes.py]] — lo importa
- [[research.runner.py]] — lo importa

_Además lo importan 3 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_ai_calls.py]]
- [[tests.test_impl_registry.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_review_fixes.py]]
