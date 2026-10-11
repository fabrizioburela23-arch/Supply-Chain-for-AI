---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/db.py"
lenguaje: "python"
lineas: 222
aliases: ["ontology/db.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/db.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 222 líneas · `ontology/db.py`

## Para qué sirve

conexión a Postgres (fuente única de verdad de la ontología).

## API pública

- `ontology_available()` _(línea 20)_
- `get_session_factory()` _(línea 104)_
- `session_scope()` — Sesión con commit/rollback automático. Uso: with session_scope() as s: ... _(línea 110)_
- `schema_outdated(engine=…)` — ¿Falta alguna de las columnas tardías? Permite detectar una base con el esquema viejo SIN tener que provocar el error en una consulta real. _(línea 141)_
- `init_schema(retries=…, delay=…)` — Crea/actualiza el esquema (idempotente). Se llama al arrancar el server y desde el script de migración. _(línea 160)_

**Internas** (empiezan con `_`): `_normalize_url`, `_env_int`, `_engine_kwargs`, `_get_engine`

## Depende de

- [[brokerage.models.py]] — importa `(dinámico: brokerage.models)`
- [[core.ops_check.py]] — importa `(dinámico: core.ops_check)`
- [[mcp_server.models.py]] — importa `(dinámico: mcp_server.models)`
- [[ontology.models.py]] — importa `Base`
- [[research.models.py]] — importa `research.models`

## Lo usan

- [[brokerage.api.py]] — lo importa
- [[brokerage.service.py]] — lo importa
- [[core.agents_api.py]] — lo importa
- [[core.ai_usage.py]] — lo importa
- [[core.decide.py]] — lo importa
- [[core.geosit.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa
- [[core.live_caps.py]] — lo importa
- [[core.ops_check.py]] — lo importa
- [[core.portfolio_advisor.py]] — lo importa
- [[core.portfolio_ai.py]] — lo importa
- [[core.portfolio_reports_api.py]] — lo importa
- [[matrix.api.py]] — lo importa
- [[mcp_server.api.py]] — lo importa
- [[mcp_server.auth.py]] — lo importa
- [[mcp_server.oauth.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[ontology.reconcile.py]] — lo importa
- [[research.api.py]] — lo importa
- [[research.auto_events.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[research.health.py]] — lo importa
- [[research.runner.py]] — lo importa
- [[scripts.audit_graph.py]] — lo importa
- [[scripts.migrate_v0_to_ontology.py]] — lo importa
- [[scripts.reconcile_v0_to_ontology.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `cancel_order` → [[API herramientas MCP]]
- herramienta MCP `get_account` → [[API herramientas MCP]]
- herramienta MCP `get_claim_evidence` → [[API herramientas MCP]]
- herramienta MCP `get_committee_memo` → [[API herramientas MCP]]
- herramienta MCP `get_company` → [[API herramientas MCP]]
- herramienta MCP `get_conclusions_board` → [[API herramientas MCP]]
- herramienta MCP `get_ontology_object` → [[API herramientas MCP]]
- herramienta MCP `get_order_status` → [[API herramientas MCP]]
- herramienta MCP `get_positions` → [[API herramientas MCP]]
- herramienta MCP `get_research` → [[API herramientas MCP]]
- herramienta MCP `get_research_job` → [[API herramientas MCP]]
- herramienta MCP `get_track_record` → [[API herramientas MCP]]
- herramienta MCP `list_orders` → [[API herramientas MCP]]
- herramienta MCP `preview_order` → [[API herramientas MCP]]
- herramienta MCP `run_committee` → [[API herramientas MCP]]
- herramienta MCP `run_research` → [[API herramientas MCP]]
- herramienta MCP `submit_order` → [[API herramientas MCP]]

_Además lo importan 30 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV DATABASE_URL]]
- [[ENV DB_CONNECT_TIMEOUT_S]]
- [[ENV DB_MAX_OVERFLOW]]
- [[ENV DB_POOL_SIZE]]
- [[ENV DB_POOL_TIMEOUT_S]]
- [[ENV DB_STATEMENT_TIMEOUT_MS]]

## Pruebas que lo cubren

- [[tests.test_agent_dudosos.py]]
- [[tests.test_ai_usage.py]]
- [[tests.test_ask_agent.py]]
- [[tests.test_brokerage.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_committee_os_narr.py]]
- [[tests.test_graph_api.py]]
- [[tests.test_infra.py]]
- [[tests.test_ingest_news.py]]
- [[tests.test_jev_router.py]]
- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_khipus_os_server.py]]
- [[tests.test_matrix.py]]
- [[tests.test_mcp.py]]
- [[tests.test_ontology.py]]
- [[tests.test_ontology_actions.py]]
- [[tests.test_ontology_agents.py]]
- [[tests.test_ontology_alerts.py]]
- [[tests.test_overnight3_diag_bilingual.py]]
- [[tests.test_overnight_ai_routing.py]]
- [[tests.test_phase3.py]]
- [[tests.test_portfolio_persist.py]]
- [[tests.test_portfolio_reports.py]]
- [[tests.test_provenance.py]]
- [[tests.test_reconcile.py]]
- [[tests.test_repair_committee.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_repair_ontology.py]]
- [[tests.test_repair_ontology_review.py]]
- [[tests.test_repair_ops.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_research.py]]
- [[tests.test_security.py]]
- [[tests.test_tensor_autolink.py]]
