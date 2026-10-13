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

- [[core.decisions.py]] — lo importa
- [[core.entities.py]] — lo importa
- [[core.portfolio_ai.py]] — lo importa
- [[core.screener.py]] — lo importa
- [[core.semantic.py]] — lo importa
- [[core.sim_agents.py]] — lo importa
- [[core.world.py]] — lo importa
- [[matrix.api.py]] — lo importa
- [[matrix.engine.py]] — lo importa
- [[matrix.tensor.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[ontology.actions.py]] — lo importa
- [[ontology.agents.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[ontology.bulk_import.py]] — lo importa
- [[ontology.db.py]] — lo importa
- [[ontology.service.py]] — lo importa
- [[research.context.py]] — lo importa
- [[research.router.py]] — lo importa
- [[scripts.build_shapes.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `get_company` → [[API herramientas MCP]]
- herramienta MCP `get_supply_chain` → [[API herramientas MCP]]
- herramienta MCP `run_committee` → [[API herramientas MCP]]
- herramienta MCP `run_research` → [[API herramientas MCP]]
- herramienta MCP `search_companies` → [[API herramientas MCP]]

_Además lo importan 15 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.gates_cases.py]]
- [[tests.test_gates_conformance.py]]
- [[tests.test_gates_ir_fresh.py]]
- [[tests.test_gates_resulting_state.py]]
- [[tests.test_governance.py]]
- [[tests.test_governance_seed_parity.py]]
- [[tests.test_hot_contract.py]]
- [[tests.test_hot_invalidation.py]]
- [[tests.test_hot_review_fixes.py]]
- [[tests.test_hot_views_parity.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_ops_graph_version.py]]
- [[tests.test_ops_single_source.py]]
- [[tests.test_review_infra_c.py]]
- [[tests.test_tensor.py]]
