---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "core/semantic.py"
lenguaje: "python"
lineas: 140
aliases: ["core/semantic.py"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# core/semantic.py

> Módulo · capa [[Capa Chat y agentes]] · 140 líneas · `core/semantic.py`

## Para qué sirve

CAPA 2 (PRECONSCIENTE): el grafo semántico activo.

## API pública

- `resolve_ids(names)` — Nombres/tickers/ids sueltos → ids canónicos del snapshot (los que existan). _(línea 55)_
- `extract_companies(question, limit=…)` — Detección barata (sin IA) de empresas mencionadas en la pregunta. _(línea 81)_
- `build_context(company_ids=…, question=…, neighbors_per_side=…)` — El contexto preconsciente: foco + vecindario + chokepoints. Compacto a propósito — está pensado para entrar en un prompt sin inflarlo. _(línea 105)_

**Internas** (empiezan con `_`): `_load_snapshot`, `_node_brief`

## Depende de

- [[ontology.vocabulary.py]] — importa `flow_degree`, `flow_relation_types`
- [[data.grafo_v0.json]] — lo nombra por su ruta

## Lo usan

- [[core.khipu_chat.py]] — lo importa
- [[core.portfolio_advisor.py]] — lo importa
- [[core.portfolio_reports_api.py]] — lo importa
- [[core.sim_agents.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_ai_usage.py]]
- [[tests.test_cleanup_server.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
