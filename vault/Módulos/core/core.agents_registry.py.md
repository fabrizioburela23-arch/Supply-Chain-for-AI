---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/agents_registry.py"
lenguaje: "python"
lineas: 56
aliases: ["core/agents_registry.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/agents_registry.py

> Módulo · capa [[Capa Infraestructura]] · 56 líneas · `core/agents_registry.py`

## Para qué sirve

el registro de agentes del lado Python (limpieza 2026-10-11).

## API pública

- `seat_agent(seat, default=…)` _(línea 50)_
- `research_types_of(agent_id)` — Tipos de analista de investigación (research/agents/registry) que pertenecen a una mascota. _(línea 54)_

**Internas** (empiezan con `_`): `_load`

## Depende de

_Nada interno._

## Lo usan

- [[core.agents_api.py]] — lo importa
- [[core.identity.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa
- [[core.voice_api.py]] — lo importa
- [[research.agent_skills.py]] — lo importa
- [[research.ask_agent.py]] — lo importa
- [[research.deliberation.py]] — lo importa
- [[research.runner.py]] — lo importa

_Además lo importan 7 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_agents_registry.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_committee_os_narr.py]]
- [[tests.test_khipus_os_server.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_voice_os_server.py]]
- [[tests.test_voice_tour.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 (b) — LIMPIEZA QUE NO QUEDEN COSAS SUELTAS (sw v254)]]
