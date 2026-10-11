---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "core/agents_api.py"
lenguaje: "python"
lineas: 448
aliases: ["core/agents_api.py"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# core/agents_api.py

> Módulo · capa [[Capa Chat y agentes]] · 448 líneas · `core/agents_api.py`

## Para qué sirve

PERFILES DE LOS AGENTES de Khipus OS (2026-10-06).

## API pública

- `aggregate_track(tr, research_types, scope=…)` — Historial de una mascota a partir de research/outcomes.track_record (puede agrupar varios analistas). scope='overall' usa el historial … _(línea 254)_
- `build_profiles(lang=…)` _(línea 364)_
- `agent_profiles_endpoint()` _(línea 428)_
- `clear_cache()` _(línea 446)_

**Internas** (empiezan con `_`): `_now`, `_n_companies`, `_need_lines`, `_tools_for`, `_pct_txt`, `_khipu_track`, `_db_ok`, `_db_part`, `_stats_for`

## Depende de

- [[core.agents_registry.py]] — importa `AGENT_BY_ID`, `research_types_of`
- [[core.entities.py]] — importa `get_index`
- [[core.http.py]] — importa `rate_limit`
- [[core.khipu_chat.py]] — importa `khipu_chat`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[research.agent_skills.py]] — importa `SKILLS`
- [[research.context.py]] — importa `AGENT_NEEDS`
- [[research.models.py]] — importa `AIUsage`, `AgentRun`, `CommitteeMemo`
- [[research.outcomes.py]] — importa `MIN_N`, `outcomes`, `reliability`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/agents/profiles` | `agent_profiles_endpoint` | [[engine.oswindows.js]], 3 pruebas |

Grupos: [[API agents]]

## Pruebas que lo cubren

- [[tests.test_agents_registry.py]]
- [[tests.test_ask_agent.py]]
- [[tests.test_khipus_os_fixes_windows.py]]
- [[tests.test_khipus_os_server.py]]
- [[tests.test_khipus_os_windows.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 (b) — LIMPIEZA QUE NO QUEDEN COSAS SUELTAS (sw v254)]]
