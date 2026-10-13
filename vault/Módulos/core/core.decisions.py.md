---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/decisions.py"
lenguaje: "python"
lineas: 901
aliases: ["core/decisions.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/decisions.py

> Módulo · capa [[Capa Infraestructura]] · 901 líneas · `core/decisions.py`

## Para qué sirve

EL servicio de decisiones (docs/INFRA_OPERATIVA.md §2.2-§2.7; paso 6 del plan).

## API pública

- clase `LedgerUnavailable` — El libro no se pudo escribir (base caída / tablas ausentes): el efecto NO debe confirmarse. _(línea 76)_
- `canonical(obj)` — bytes canónicos: claves ordenadas, separadores compactos, UTF-8, sin NaN/Infinity. _(línea 81)_
- `sha256_hex(b)` _(línea 99)_
- `pii_key()` — (clave, key_id, débil). k_pii = HKDF(SECRET_KEY, 'khipus-ledger-pii'); key_id NO revela la clave. _(línea 114)_
- `pii_hmac(text, lang=…)` — Huella de un texto personal: {hmac, key_id, len, lang}. En producción con SECRET_KEY por defecto no se calcula (sería forjable): … _(línea 126)_
- `code_sha()` _(línea 150)_
- `stamp()` — graph_version y linaje del grafo (en memoria, sin SQL), release_hash y code_sha. _(línea 155)_
- `default_durability(kind)` _(línea 179)_
- clase `DecisionCtx` — Se llena desde los puntos instrumentados (apply_event → effect) o a mano. Nunca escribe por sí solo. _(línea 184)_
- `current()` _(línea 289)_
- `note_event(ev)` — Hook de ontology.service.apply_event: cada evento escrito dentro de un scope es un EFECTO de la decisión. _(línea 293)_
- `record(session, ctx, status=…, output=…, expires_at=…)` — Escribe la decisión. sync: en la MISMA sesión que el efecto (si falla, lanza y el caller revierte todo). async: sesión autónoma, nunca … _(línea 455)_
- `safe_error(exc)` — Resumen del error SIN valores de entrada (Pydantic incluye el input del usuario en sus errores). _(línea 511)_
- `record_rejection(ctx, status=…, error=…, report=…)` — Rechazo/bloqueo/fallo en una sesión AUTÓNOMA: queda aunque el caller revierta su transacción. Nunca lanza (devuelve None si ni siquiera se … _(línea 532)_
- `decision_scope(kind, principal, session, subject=…, durability=…, parent_id=…, supersedes_id=…, correlation_id=…, valid_at=…, rejection_status=…, decision_id=…)` — Reserva decision_id, marca la transacción (`khipus.decision_id`, guardia del paso 22) y abre el contexto. Al salir: … _(línea 572)_
- `approve(session, target_id, principal, verdict=…, effective_from=…, note=…)` — approval.grant | approval.deny con parent_id = la decisión aprobada. Exige un HUMANO con PIN; si quien pidió fue un agente, una IA (MCP) o … _(línea 619)_
- `link(session, decision_id, role, ref_kind, ref_id, ref_hash=…, as_of=…, **note)` — Añade una referencia DESPUÉS (solo INSERT; repetirla es un no-op). _(línea 659)_
- `link_effect(session, decision_id, ref_kind, ref_id, **note)` _(línea 668)_
- `outcome(session, decision_id, outcome_kind, result, observed_at, source)` — Resultado posterior (nunca se pisa; el vigente es el último). Con result['dedup_key'] no se repite. _(línea 672)_
- `supersede(session, old_id, principal, reason, kind=…, output=…)` — Corrección: decisión NUEVA con supersedes_id (nunca un UPDATE). 'superseded' se deriva, no es un estado. _(línea 683)_
- `list_decisions(session, kind=…, principal=…, status=…, entity=…, since=…, limit=…, redact=…)` _(línea 724)_
- `get(session, decision_id, redact=…, with_blobs=…)` _(línea 743)_
- `explain(d, lang=…)` — Explicación de una línea en lenguaje simple (ES/EN) a partir de get(..., redact=False). _(línea 782)_
- `stats()` _(línea 798)_
- `submit_async(build, status=…)` — Encola `build()` → DecisionCtx | (DecisionCtx, after) | None. Corre en el hilo del libro; `after(decision_id)` (opcional) corre tras … _(línea 812)_
- `flush_async(timeout=…)` — Escribe ya lo encolado (pruebas y apagado). → cuántas se procesaron. _(línea 849)_
- `async_pending()` _(línea 899)_

**Internas** (empiezan con `_`): `_json_default`, `_hkdf`, `_tables`, `_manifest`, `_rows`, `_dumps`, `_insert`, `_lineage`, `_g8`, `_autonomous`, `_set_guc`, `_uuid`, `_row_dict`, `_run_async_item`, `_ensure_async_writer`

## Depende de

- [[core.__init__.py]] — importa `focus`, `gates`, `report`, `signals`
- [[core.governance.py]] — importa `governance`
- [[core.ledger.py]] — importa `ledger`
- [[core.pin.py]] — importa `DEFAULT_SECRET_KEY`, `in_production`, `secret_key_default`
- [[ontology.bulk_import.py]] — importa `(dinámico: ontology.bulk_import)`
- [[ontology.db.py]] — importa `get_session_factory`, `ontology_available`
- [[ontology.ledger_models.py]] — importa `Decision`, `DecisionBlob`, `DecisionOutcome`, `DecisionRef`, `DecisionViolation`

## Lo usan

- [[brokerage.service.py]] — lo importa
- [[core.ai_calls.py]] — lo importa
- [[core.decide.py]] — lo importa
- [[core.decision_sites.py]] — lo importa
- [[core.governance.py]] — lo importa
- [[core.governance_flow.py]] — lo importa
- [[core.impls.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa
- [[core.ledger.py]] — lo importa
- [[core.ledger_api.py]] — lo importa
- [[core.prices_api.py]] — lo importa
- [[core.prices_store.py]] — lo importa
- [[core.replay.py]] — lo importa
- [[core.retention.py]] — lo importa
- [[core.trading_agent.py]] — lo importa
- [[core.voice_api.py]] — lo importa
- [[matrix.api.py]] — lo importa
- [[mcp_server.api.py]] — lo importa
- [[mcp_server.oauth.py]] — lo importa
- [[ontology.actions.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[ontology.checkpoints.py]] — lo importa
- [[ontology.reconcile.py]] — lo importa
- [[ontology.service.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.runner.py]] — lo importa
- [[scripts.build_governance.py]] — lo importa
- [[scripts.build_shapes.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 25 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV RAILWAY_GIT_COMMIT_SHA]]
- [[ENV SECRET_KEY]]

## Pruebas que lo cubren

- [[tests.conftest.py]]
- [[tests.gates_cases.py]]
- [[tests.test_ai_calls.py]]
- [[tests.test_cierre_defectos.py]]
- [[tests.test_cierre_infra.py]]
- [[tests.test_gates_ir_fresh.py]]
- [[tests.test_gates_resulting_state.py]]
- [[tests.test_governance.py]]
- [[tests.test_governance_flow.py]]
- [[tests.test_impl_registry.py]]
- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_core.py]]
- [[tests.test_ledger_guard.py]]
- [[tests.test_ledger_privacy.py]]
- [[tests.test_ledger_review_fixes.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_retention_purge.py]]
- [[tests.test_review_batch_g.py]]
- [[tests.test_review_infra_c.py]]
- [[tests.test_rutas_acceso_decision.py]]
- [[tests.test_scenario_pnl.py]]
- [[tests.test_voice_agent_split.py]]
