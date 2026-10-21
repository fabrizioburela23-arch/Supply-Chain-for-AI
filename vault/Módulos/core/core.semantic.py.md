---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "core/semantic.py"
lenguaje: "python"
lineas: 144
aliases: ["core/semantic.py"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# core/semantic.py

> Módulo · capa [[Capa Chat y agentes]] · 144 líneas · `core/semantic.py`

## Para qué sirve

CAPA 2 (PRECONSCIENTE): el grafo semántico activo.

## API pública

- `graph_version()` — La generación del grafo que usa la capa semántica (tests/test_ops_single_source.py). _(línea 59)_
- `resolve_ids(names)` — Nombres/tickers/ids sueltos → ids canónicos del snapshot (los que existan). _(línea 64)_
- `extract_companies(question, limit=…)` — Empresas mencionadas en la pregunta (sin IA) — EL detector del motor de contexto (core/context_engine.detect, BRECHAS L4-01). Antes era una … _(línea 90)_
- `build_context(company_ids=…, question=…, neighbors_per_side=…)` — El contexto preconsciente: foco + vecindario + chokepoints. Compacto a propósito — está pensado para entrar en un prompt sin inflarlo. _(línea 104)_

**Internas** (empiezan con `_`): `_build`, `_load_snapshot`, `_node_brief`

## Depende de

- [[core.__init__.py]] — importa `hot`
- [[core.context_engine.py]] — importa `detect`, `rank_neighbors`
- [[ontology.vocabulary.py]] — importa `flow_relation_types`

## Lo usan

- [[core.khipu_chat.py]] — lo importa
- [[core.portfolio_advisor.py]] — lo importa
- [[core.portfolio_reports_api.py]] — lo importa
- [[core.sim_agents.py]] — lo importa
- [[core.sim_report.py]] — lo importa
- [[core.trading_agent.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `run_scenario` → [[API herramientas MCP]]

_Además lo importan 5 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_ai_usage.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_context_engine.py]]
- [[tests.test_ops_single_source.py]]
- [[tests.test_scenario_kernel.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
