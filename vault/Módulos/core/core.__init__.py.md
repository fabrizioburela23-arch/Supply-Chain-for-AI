---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/__init__.py"
lenguaje: "python"
lineas: 13
aliases: ["core/__init__.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/__init__.py

> Módulo · capa [[Capa Infraestructura]] · 13 líneas · `core/__init__.py`

## Para qué sirve

helpers compartidos entre server.py (Flask) y ontology/ (agentes).

## API pública

_Sin funciones ni clases públicas de nivel superior._

## Depende de

_Nada interno._

## Lo usan

- [[brokerage.service.py]] — lo importa
- [[core.context_engine.py]] — lo importa
- [[core.decision_sites.py]] — lo importa
- [[core.decisions.py]] — lo importa
- [[core.entities.py]] — lo importa
- [[core.governance_flow.py]] — lo importa
- [[core.governance_preview.py]] — lo importa
- [[core.governance_shadow.py]] — lo importa
- [[core.impls.py]] — lo importa
- [[core.instruments.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa
- [[core.portfolio_ai.py]] — lo importa
- [[core.replay.py]] — lo importa
- [[core.scenario_engine.py]] — lo importa
- [[core.screener.py]] — lo importa
- [[core.semantic.py]] — lo importa
- [[core.sim_agents.py]] — lo importa
- [[core.world.py]] — lo importa
- [[matrix.api.py]] — lo importa
- [[matrix.engine.py]] — lo importa
- [[matrix.tensor.py]] — lo importa
- [[matrix.tensor_api.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[ontology.actions.py]] — lo importa
- [[ontology.agents.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[ontology.bitemporal.py]] — lo importa
- [[ontology.bulk_import.py]] — lo importa
- [[ontology.db.py]] — lo importa
- [[ontology.service.py]] — lo importa
- [[research.agent_skills.py]] — lo importa
- [[research.context.py]] — lo importa
- [[research.router.py]] — lo importa
- [[scripts.build_shapes.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `calculate_correlation` → [[API herramientas MCP]]
- herramienta MCP `get_company` → [[API herramientas MCP]]
- herramienta MCP `get_exposure` → [[API herramientas MCP]]
- herramienta MCP `get_history` → [[API herramientas MCP]]
- herramienta MCP `get_supply_chain` → [[API herramientas MCP]]
- herramienta MCP `run_committee` → [[API herramientas MCP]]
- herramienta MCP `run_research` → [[API herramientas MCP]]
- herramienta MCP `run_scenario` → [[API herramientas MCP]]
- herramienta MCP `search_companies` → [[API herramientas MCP]]

_Además lo importan 31 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.gates_cases.py]]
- [[tests.test_bitemporal.py]]
- [[tests.test_bitemporal_review.py]]
- [[tests.test_cierre_infra.py]]
- [[tests.test_gates_conformance.py]]
- [[tests.test_gates_ir_fresh.py]]
- [[tests.test_gates_orders_parity.py]]
- [[tests.test_gates_resulting_state.py]]
- [[tests.test_governance.py]]
- [[tests.test_governance_activation.py]]
- [[tests.test_governance_flow.py]]
- [[tests.test_governance_seed_parity.py]]
- [[tests.test_hot_contract.py]]
- [[tests.test_hot_invalidation.py]]
- [[tests.test_hot_review_fixes.py]]
- [[tests.test_hot_views_parity.py]]
- [[tests.test_kernel_monotone_severity.py]]
- [[tests.test_kernel_reference_figures.py]]
- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_mcp.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_ops_graph_version.py]]
- [[tests.test_ops_single_source.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_review_batch_g.py]]
- [[tests.test_review_infra_c.py]]
- [[tests.test_review_lists.py]]
- [[tests.test_scenario_kernel.py]]
- [[tests.test_tensor.py]]
