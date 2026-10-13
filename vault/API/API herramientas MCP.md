---
tipo: "api"
capa: "MCP y API"
herramientas: 29
tags: ["capa/mcp-api", "tipo/api"]
---

# API herramientas MCP

> 29 herramientas definidas en [[mcp_server.tools.py]] (y las v2 en [[mcp_server.ops.py]]) y servidas por [[mcp_server.api.py]] en `POST /mcp` (JSON-RPC). Alcances: **read** (consultas), **research** (gasta presupuesto de IA), **trade** (solo PROPONE órdenes; siempre aprobación humana).

| Herramienta | Alcance | Solo lectura | Función | Módulos que usa |
|---|---|---|---|---|
| `calculate_correlation` | read | sí | `t_calculate_correlation` | [[core.__init__.py]], [[core.entities.py]], [[core.risk_report.py]] |
| `cancel_order` | trade | **no** | `t_cancel_order` | [[brokerage.service.py]], [[mcp_server.contract.py]], [[ontology.db.py]] |
| `find_similar_entities` | read | sí | `t_find_similar_entities` | [[matrix.tensor.py]] |
| `get_account` | trade | sí | `t_get_account` | [[brokerage.service.py]], [[mcp_server.contract.py]], [[ontology.db.py]] |
| `get_claim_evidence` | read | sí | `t_get_claim_evidence` | [[core.numbers.py]], [[mcp_server.contract.py]], [[ontology.db.py]], [[ontology.models.py]], [[ontology.provenance.py]], [[research.models.py]] |
| `get_committee_memo` | read | sí | `t_get_committee_memo` | [[core.entities.py]], [[mcp_server.contract.py]], [[ontology.db.py]], [[research.committee.py]] |
| `get_company` | read | sí | `t_get_company` | [[core.__init__.py]], [[core.entities.py]], [[core.world.py]], [[matrix.tensor.py]], [[mcp_server.contract.py]], [[ontology.agents.py]], [[ontology.db.py]], [[ontology.models.py]], [[ontology.vocabulary.py]] |
| `get_conclusions_board` | read | sí | `t_get_conclusions_board` | [[mcp_server.contract.py]], [[ontology.db.py]], [[research.committee.py]] |
| `get_exposure` | read | sí | `t_get_exposure` | [[core.__init__.py]], [[core.portfolio_advisor.py]], [[core.quotes.py]], [[matrix.tensor.py]] |
| `get_history` | read | sí | `t_get_history` | [[core.__init__.py]], [[core.entities.py]], [[core.risk_report.py]] |
| `get_ontology_object` | read | sí | `t_get_ontology_object` | [[core.entities.py]], [[mcp_server.contract.py]], [[ontology.bitemporal.py]], [[ontology.db.py]], [[ontology.models.py]], [[ontology.provenance.py]], [[ontology.service.py]] |
| `get_option_greeks` | read | sí | `t_get_option_greeks` | [[core.options.py]], [[mcp_server.contract.py]] |
| `get_order_status` | trade | sí | `t_get_order_status` | [[brokerage.service.py]], [[mcp_server.contract.py]], [[ontology.db.py]] |
| `get_positions` | trade | sí | `t_get_positions` | [[brokerage.service.py]], [[mcp_server.contract.py]], [[ontology.db.py]] |
| `get_research` | read | sí | `t_get_research` | [[core.entities.py]], [[core.numbers.py]], [[mcp_server.contract.py]], [[ontology.db.py]], [[research.models.py]], [[research.runner.py]] |
| `get_research_health` | read | sí | `t_get_research_health` | [[mcp_server.contract.py]], [[research.health.py]] |
| `get_research_job` | read | sí | `t_get_research_job` | [[mcp_server.contract.py]], [[ontology.db.py]], [[research.models.py]], [[research.runner.py]] |
| `get_risk_report` | read | sí | `t_get_risk_report` | [[core.risk_report.py]], [[mcp_server.contract.py]] |
| `get_subgraph` | read | sí | `t_get_subgraph` | [[core.context_engine.py]] |
| `get_supply_chain` | read | sí | `t_get_supply_chain` | [[core.__init__.py]], [[core.entities.py]], [[mcp_server.contract.py]], [[ontology.vocabulary.py]] |
| `get_track_record` | read | sí | `t_get_track_record` | [[mcp_server.contract.py]], [[ontology.db.py]], [[research.outcomes.py]] |
| `get_world_events` | read | sí | `t_get_world_events` | [[core.gpr.py]], [[core.world.py]], [[mcp_server.contract.py]] |
| `list_orders` | trade | sí | `t_list_orders` | [[brokerage.service.py]], [[mcp_server.contract.py]], [[ontology.db.py]] |
| `preview_order` | trade | **no** | `t_preview_order` | [[brokerage.service.py]], [[mcp_server.contract.py]], [[ontology.db.py]] |
| `run_committee` | research | **no** | `t_run_committee` | [[brokerage.service.py]], [[core.__init__.py]], [[core.entities.py]], [[core.identity.py]], [[mcp_server.contract.py]], [[ontology.db.py]], [[ontology.vocabulary.py]], [[research.committee.py]] |
| `run_research` | research | **no** | `t_run_research` | [[core.__init__.py]], [[core.ai.py]], [[core.entities.py]], [[mcp_server.contract.py]], [[ontology.db.py]], [[ontology.vocabulary.py]], [[research.runner.py]] |
| `run_scenario` | read | sí | `t_run_scenario` | [[core.__init__.py]], [[core.context_engine.py]], [[core.scenario_engine.py]], [[core.semantic.py]] |
| `search_companies` | read | sí | `t_search_companies` | [[core.__init__.py]], [[core.entities.py]], [[mcp_server.contract.py]], [[ontology.vocabulary.py]] |
| `submit_order` | trade | **no** | `t_submit_order` | [[brokerage.service.py]], [[mcp_server.contract.py]], [[ontology.db.py]] |

El chat de Khipu ([[core.khipu_chat.py]]) reutiliza estas mismas herramientas, solo las de lectura.
