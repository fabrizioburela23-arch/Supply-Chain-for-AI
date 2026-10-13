---
tipo: "modulo"
capa: "MCP y API"
ruta: "mcp_server/tools.py"
lenguaje: "python"
lineas: 1877
aliases: ["mcp_server/tools.py"]
tags: ["capa/mcp-api", "tipo/modulo"]
---

# mcp_server/tools.py

> Módulo · capa [[Capa MCP y API]] · 1.877 líneas · `mcp_server/tools.py`

## Para qué sirve

catálogo de herramientas MCP de Khipus.

## API pública

- clase `ToolError` — Error de EJECUCIÓN de la herramienta → resultado con isError: true. _(línea 48)_
- clase `InvalidParams` — Argumentos que no cumplen el inputSchema → JSON-RPC -32602. _(línea 63)_
- clase `Tool` _(línea 75)_
- `tool(name, title, scope, description, properties=…, required=…, read_only=…, destructive=…, idempotent=…, open_world=…)` _(línea 92)_
- `validate(schema, args, path=…)` _(línea 165)_
- clase `Ctx` _(línea 190)_
- `visible_tools(principal)` _(línea 197)_
- `trading_enabled()` _(línea 208)_
- `call(name, args, ctx, shape=…)` — → dict (éxito). Lanza ToolError (isError) o InvalidParams (-32602). shape=True (el servidor MCP): aplica el contrato común (detail / … _(línea 212)_
- `graph_version()` — La generación del grafo que usan las herramientas MCP (tests/test_ops_single_source.py). _(línea 305)_
- `relation_class(rel_type)` _(línea 368)_
- `flow_types()` — Tipos de FLUJO (= proveedor/cliente), leídos del vocabulario. _(línea 372)_
- `t_search_companies(ctx, query, limit=…)` _(línea 589)_
- `t_get_company(ctx, id_or_ticker, include_live=…)` _(línea 609)_
- `t_get_supply_chain(ctx, id, direction=…, depth=…, min_weight=…, limit=…, include_partners=…)` _(línea 747)_
- `t_get_ontology_object(ctx, id, events_limit=…, as_of=…, known_at=…)` _(línea 848)_
- `t_get_research(ctx, entity, limit=…)` _(línea 989)_
- `t_get_claim_evidence(ctx, claim_id)` _(línea 1051)_
- `t_get_research_job(ctx, job_id)` _(línea 1125)_
- `t_get_risk_report(ctx, positions, horizon_days=…)` _(línea 1173)_
- `t_get_option_greeks(ctx, options)` _(línea 1198)_
- `t_get_world_events(ctx, layers=…, window=…, limit=…)` _(línea 1224)_
- `t_get_committee_memo(ctx, entity=…, memo_id=…)` _(línea 1286)_
- `t_get_conclusions_board(ctx, limit=…, side=…)` _(línea 1322)_
- `t_get_research_health(ctx, fresh=…)` _(línea 1359)_
- `t_get_track_record(ctx, agent_type=…)` _(línea 1370)_
- `t_replay_decision(ctx, decision_id)` _(línea 1394)_
- `t_run_research(ctx, entity, depth=…, only_missing=…)` _(línea 1426)_
- `t_run_committee(ctx, entity, client_id=…)` _(línea 1529)_
- `t_get_account(ctx)` _(línea 1666)_
- `t_get_positions(ctx)` _(línea 1682)_
- `t_preview_order(ctx, symbol, side, rationale, notional=…, qty=…, order_type=…, limit_price=…)` _(línea 1716)_
- `t_submit_order(ctx, preview_id)` _(línea 1751)_
- `t_list_orders(ctx, status=…, limit=…)` _(línea 1787)_
- `t_cancel_order(ctx, order_id)` _(línea 1802)_
- `t_get_order_status(ctx, order_id)` _(línea 1825)_
- `catalog()` — Para la UI / docs: todas las herramientas con su alcance. _(línea 1845)_
- `reset_caches()` _(línea 1850)_

**Internas** (empiezan con `_`): `_now_iso`, `_coerce`, `_bounded`, `_snapshot`, `_private_valuations`, `_link_trust`, `_resolve`, `_resolve_or_fail`, `_listed`, `_brief`, `_search`, `_edges`, `_distinct_pairs`, `_neighbor`, `_nrs`, `_live_profile`, `_margin_pct`, `_need_db`, `_iso`, `_with_genesis`, `_ontology_object_at`, `_claim_brief`, `_unsupported_money`, `_deferred_next`, `_job_coverage`, `_module`, `_trim_memo`, `_run_committee_async`, `_brokerage`, `_trade_ctx`, `_session`, `_mode_badge`, `_client_public`, `_order_public`, `_own_order`, `_prefer_canonical`, `_entity_ids_for`

Define **24 herramientas MCP** → [[API herramientas MCP]]

## Depende de

- [[brokerage.service.py]] — importa `(dinámico: brokerage.service)`
- [[core.__init__.py]] — importa `card`, `geo`, `hot`
- [[core.ai.py]] — importa `_ai_configured`
- [[core.company_data.py]] — importa `get_live_profile`
- [[core.entities.py]] — importa `entity_ids_for`, `get_index`, `norm`, `resolve`
- [[core.gpr.py]] — importa `(dinámico: core.gpr)`
- [[core.identity.py]] — importa `identity`
- [[core.numbers.py]] — importa `evidence_numbers`, `unsupported_money`
- [[core.options.py]] — importa `vega_report`
- [[core.replay.py]] — importa `replay`
- [[core.risk_report.py]] — importa `build_report`
- [[core.world.py]] — importa `(dinámico: core.world)`, `client_nrs`
- [[matrix.tensor.py]] — importa `(dinámico: matrix.tensor)`
- [[mcp_server.auth.py]] — importa `auth`
- [[mcp_server.contract.py]] — importa `COMMON_PROPS`, `contract`
- [[mcp_server.ops.py]] — importa `ops`
- [[ontology.agents.py]] — importa `_compute_server_nrs`
- [[ontology.bitemporal.py]] — importa `bitemporal`
- [[ontology.db.py]] — importa `session_scope`
- [[ontology.models.py]] — importa `Event`, `LinkRecord`, `ObjectRecord`
- [[ontology.provenance.py]] — importa `provenance_for_object`, `source_to_dict`
- [[ontology.service.py]] — importa `OntologyError`, `VALID_FROM_NOTE_EN`, `VALID_FROM_NOTE_ES`, `_links_active_at`, `_parse_dt`, `_utcnow`, `is_genesis`
- [[ontology.vocabulary.py]] — importa `UNVERIFIED_CONF`, `UNVERIFIED_RX`, `vocabulary`
- [[research.committee.py]] — importa `(dinámico: research.committee)`, `fail_memo`, `progress_clear`, `run_committee`
- [[research.health.py]] — importa `(dinámico: research.health)`
- [[research.models.py]] — importa `AgentRun`, `ClaimRelation`, `ResearchClaim`, `ResearchEvidence`, `ResearchJob`, `errors_of`, `open_questions_of`
- [[research.outcomes.py]] — importa `(dinámico: research.outcomes)`
- [[research.runner.py]] — importa `(dinámico: research.runner)`, `job_coverage`, `queue_position`, `research_queue_state`
- [[nodes.private_valuations.js]] — lo nombra por su ruta

## Lo usan

- [[core.khipu_chat.py]] — lo importa
- [[core.ops_check.py]] — lo importa
- [[matrix.tensor.py]] — lo importa
- [[mcp_server.api.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- [[mcp_server.protocol.py]] — lo importa

_Además lo importan 20 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV MCP_TRADING_ENABLED]]
- [[ENV RESEARCH_DAILY_BUDGET_USD]]

## Pruebas que lo cubren

- [[tests.test_bitemporal.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_context_engine.py]]
- [[tests.test_hot_views_parity.py]]
- [[tests.test_jev_router.py]]
- [[tests.test_khipu_chat.py]]
- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_khipus_os_fixes_windows.py]]
- [[tests.test_khipus_os_server.py]]
- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_ledger_review_fixes.py]]
- [[tests.test_mcp.py]]
- [[tests.test_mcp_contract.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_ops_single_source.py]]
- [[tests.test_overnight_ai_routing.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_tensor.py]]
