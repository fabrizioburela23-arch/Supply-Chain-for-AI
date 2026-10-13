---
tipo: "modulo"
capa: "Comité"
ruta: "research/committee.py"
lenguaje: "python"
lineas: 2283
aliases: ["research/committee.py"]
tags: ["capa/comite", "tipo/modulo"]
---

# research/committee.py

> Módulo · capa [[Capa Comité]] · 2.283 líneas · `research/committee.py`

## Para qué sirve

PHASE 3 · COMITÉ DE INVERSIÓN automatizado.

## API pública

- `validation_status(agent_types, table)` — C6: ¿cada analista presente tiene historial suficiente (≥ MIN_N finales)? {status: validated|partial|unvalidated, validated, min_n, … _(línea 88)_
- `quorum_check(present)` — C7: fundamental obligatorio + al menos MIN_AGENTS de QUORUM_POOL con conclusiones. _(línea 116)_
- `conviction_by_horizon(claims, contradicted_ids=…, calib=…, reliab=…)` — claims: [{id, agent_type, stance, horizon, confidence}] (activas). calib(agent_type, raw) → calibrada · reliab(agent_type) → fiabilidad … _(línea 150)_
- `agent_views(conv)` — Postura neta ponderada de cada agente (todas las horizontes con peso). _(línea 214)_
- `mandate_from(client)` — Normaliza el mandato del cliente (brokerage) → fracciones. Claves aceptadas (en %): risk_budget_pct, max_position_pct, min_vol_pct; listas … _(línea 237)_
- `alpaca_symbol(symbol)` — Ticker del catálogo (Yahoo) → símbolo de Alpaca: MOG-A → MOG.A; NVDA igual. _(línea 278)_
- `decide(overall, investable=…, insufficient=…, has_position=…, current_w=…, target_w=…, blocked=…, tradable=…, quorum=…)` — Decisión por umbrales fijos. Devuelve (decisión, motivo_es, motivo_en). tradable=False (cotiza fuera de EE.UU.: Alpaca no la opera) → una … _(línea 285)_
- `target_weight(vol_ann_pct, mandate)` — Peso objetivo por volatilidad: presupuesto_de_riesgo / vol (tope del mandato). _(línea 329)_
- `effective_target_weight(vol_ann_pct, mandate, validated=…)` — Peso objetivo con el que se DECIDE y se DIMENSIONA (mismo número en decide() y en compute_sizing): min(presupuesto/vol, tope) × … _(línea 338)_
- `compute_sizing(decision, vol_ann_pct, mandate, equity=…, current_value=…, current_qty=…, price=…, buying_power=…, trim_reason=…, price_is_usd=…, validated=…)` — Tamaño de la orden (determinista) con la cuenta en texto es/en. Topes, en orden: mandato (máx. por posición), poder de compra y los límites … _(línea 348)_
- clase `ThesisItem` _(línea 497)_
- clase `RiskItem` _(línea 512)_
- clase `DissentItem` _(línea 518)_
- clase `ConclusionItem` _(línea 525)_
- clase `ChairMemo` _(línea 531)_
- `chair_checks(obj, valid_refs, quant_decision, min_date, max_date, evidence_items, agent_types)` _(línea 624)_
- `brokerage_service()` — brokerage.service si está instalado y disponible; si no, None. _(línea 684)_
- `build_package(label, symbol, claims_by_id, conv, overall, rels, live, risk, sizing, decision, reason_es, client)` — Paquete NUMERADO para el presidente + items para el guardián de cifras. _(línea 787)_
- `deterministic_memo(label, decision, reason_es, reason_en, conv, overall, claims_by_id, cref, views, rels, risk, review_date, ai_error=…, ai_error_en=…)` — Memo SIN IA: plantillas sobre los números del núcleo (siempre disponible). _(línea 856)_
- `progress_set(memo_id, stage, **extra)` _(línea 980)_
- `progress_say(memo_id, *msgs)` — Publica mensajes de la sala del comité (research/deliberation) EN VIVO. _(línea 995)_
- `progress_get(memo_id)` _(línea 1011)_
- `progress_clear(memo_id)` _(línea 1024)_
- `run_committee(session, entity_id, requested_by, client_id=…, provider=…, deps=…, memo_id=…)` — Corre el comité completo y persiste el memo. Devuelve el memo (dict). _(línea 1029)_
- `memo_dict(m, redact_client=…)` _(línea 1704)_
- `falsified_in_memo(session, m)` — C8: conclusiones de ESTE memo que el mercado ya falsó (regla verificable). _(línea 1747)_
- `get_memo(session, memo_id, redact_client=…)` _(línea 1761)_
- `latest_memo(session, entity_id, redact_client=…)` _(línea 1769)_
- `list_memos(session, entity_id=…, limit=…)` _(línea 1777)_
- `approve_memo(session, memo_id, actor, note=…, brokerage=…)` — Aprobación HUMANA (la ruta exige PIN). Con cliente y decisión accionable crea una PREVISUALIZACIÓN de orden en brokerage … _(línea 1820)_
- `reject_memo(session, memo_id, actor, reason=…, brokerage=…)` — Rechazo humano. Si el memo ya tenía una orden esperando aprobación en Clientes, se RETIRA (brokerage.reject_preview) — si no, un humano … _(línea 1925)_
- `memo_allows_order(session, memo_id, preview_id=…)` — SEGUNDO CANDADO (lo llama brokerage.service._execute antes de enviar una orden source='committee'): solo se envía si su memo está … _(línea 1973)_
- `mark_executed(session, memo_id, order=…, actor=…)` — Para el módulo de corretaje: la orden del memo se ejecutó. Nunca espera un bloqueo (SKIP LOCKED): la llama el corretaje con su orden … _(línea 1987)_
- `fail_memo(session, memo_id, error, error_en=…)` _(línea 2008)_
- `create_placeholder(session, entity_id, requested_by, client_id=…)` — Fila 'running' para correr el comité en segundo plano (la API la consulta). _(línea 2017)_
- `acquire_run_slot()` — Cupo para correr un comité (no bloquea). False → responder 429. _(línea 2046)_
- `release_run_slot()` _(línea 2051)_
- `recent_memo(session, entity_id, client_id=…, now=…)` — Memo reutilizable para el mismo (entidad, cliente): uno que sigue deliberando, o uno propuesto hace menos de REUSE_DONE_MIN. Los 'running' … _(línea 2058)_
- `invalidate_board_cache()` _(línea 2102)_
- `board(session, limit=…)` _(línea 2132)_
- `refresh_targets(session, max_n=…, stale_days=…, entities=…)` — Qué empresas investigar al pulsar «Actualizar» en la Pizarra: las pedidas, o las de investigación más vieja (> stale_days), o — pizarra … _(línea 2243)_

**Internas** (empiezan con `_`): `_now`, `_ttl_hours`, `_frac`, `_usd_or_none`, `_decide_core`, `_downgrade_reason`, `_schema_hint`, `_money_check`, `_default_risk`, `_default_live`, `_bounded`, `_daily_used`, `_same_symbol`, `_client_context`, `_fmt_pct`, `_audit`, `_resolve_entity`, `_dominant_horizon`, `_run_committee`, `_ai_ready`, `_entity_node`, `_entity_listed`, `_unlisted_tech_lines`, `_room_names`, `_mascot_voice`, `_research_request_lines`, `_auto_research`, `_seat_run`, `_run_debate`, `_src_dict`, `_evidence_rows`, `_top_evidence`, `_chair`, `_scrub`, `_redact_audit`, `_client_mode`, `_lock_memo`, `_err`, `_preview_error`, `_max_concurrent`, `_board_fingerprint`, `_board_uncached`, `_prefer_canonical`, `_entity_ids_for`

## Depende de

- [[brokerage.service.py]] — importa `(dinámico: brokerage.service)`
- [[core.ai_usage.py]] — importa `ai_context`
- [[core.company_data.py]] — importa `get_live_profile`
- [[core.entities.py]] — importa `UMBRAL_BUSQUEDA`, `entity_ids_for`, `get_index`, `resolve`
- [[core.live_facts.py]] — importa `_fact_for`
- [[core.numbers.py]] — importa `check_numbers`
- [[core.risk_report.py]] — importa `build_report`
- [[research.agent_skills.py]] — importa `join_names`, `seat_call_name`, `working_line`
- [[research.debate.py]] — importa `debate`
- [[research.deliberation.py]] — importa `AGENT_NAMES`, `deliberation`
- [[research.errors.py]] — importa `friendly`
- [[research.falsifiers.py]] — importa `FalsifierRule`, `direction_errors`
- [[research.llm.py]] — importa `LLMError`, `RoutedProvider`, `estimate_cost`, `route_for`
- [[research.models.py]] — importa `AgentRun`, `ClaimRelation`, `CommitteeMemo`, `DECISIONS`, `HORIZONS`, `ResearchClaim`, `ResearchEvidence`, `errors_of`
- [[research.outcomes.py]] — importa `MIN_N`, `agent_reliability`, `calibrated_confidence`, `calibration_table`, `is_us_listing`, `symbol_for`
- [[research.runner.py]] — importa `_cfg`, `create_job`, `execute_job`, `spent_today`

## Lo usan

- [[brokerage.service.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa
- [[core.portfolio_advisor.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[research.ask_agent.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- herramienta MCP `get_committee_memo` → [[API herramientas MCP]]
- herramienta MCP `get_conclusions_board` → [[API herramientas MCP]]
- herramienta MCP `run_committee` → [[API herramientas MCP]]

_Además lo importan 14 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV COMMITTEE_MAX_CONCURRENT]]
- [[ENV COMMITTEE_MEMO_TTL_HOURS]]

## Pruebas que lo cubren

- [[tests.test_block0_committee.py]]
- [[tests.test_block0_numbers.py]]
- [[tests.test_block0_review.py]]
- [[tests.test_brokerage.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_committee_os_narr.py]]
- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_khipus_os_server.py]]
- [[tests.test_mcp.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_phase3.py]]
- [[tests.test_repair_committee.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_repair_review2.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-09 — EL COMITÉ ENTRA A KHIPUS OS (sw v250)]]
- [[Sesión 2026-10-02 (b) — COMITÉ CON ANÁLISIS REAL DE IA + INVESTIGACIÓN QUE NO SE CAE]]
- [[Sesión 2026-10-02 — SALA DEL COMITÉ - PUESTOS + DEBATE EN VIVO (sw v175)]]
