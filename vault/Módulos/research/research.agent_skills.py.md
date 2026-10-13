---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "research/agent_skills.py"
lenguaje: "python"
lineas: 410
aliases: ["research/agent_skills.py"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# research/agent_skills.py

> Módulo · capa [[Capa Chat y agentes]] · 410 líneas · `research/agent_skills.py`

## Para qué sirve

HABILIDADES PROPIAS de cada agente (2026-10-06).

## API pública

- `seat_mascot(seat)` — Id de la mascota de un puesto ('fundamental' → 'analista'); None si no tiene. _(línea 118)_
- `seat_call_name(seat, lang=…)` — Cómo se nombra a un analista en la sala: 'Analista (fundamental)', 'Radar (noticias)', 'Técnico', 'Cadena'. _(línea 123)_
- `join_names(names, lang=…)` — ['A', 'B', 'C'] → 'A, B y C' (en: 'A, B and C'). _(línea 134)_
- `working_line(seat)` — (es, en): lo que hace este analista mientras investiga. _(línea 182)_
- `role_actions(seat, eid, label, listed)` _(línea 188)_
- `skill_packet(seat, eid)` — → {text, facts, sources, n_evidence, ok}. Corre la evidencia del rol y sus extras EN PARALELO; nunca lanza. _(línea 355)_
- `note_for(seat, label, facts, lang=…)` — Resumen DETERMINISTA (para la tarjeta de aportes del chat): solo valores de `facts`. _(línea 390)_

**Internas** (empiezan con `_`): `_fmt_pct`, `_supply_extras`, `_geo_extras`, `_news_extras`, `_fund_extras`, `_macro_extras`, `_context`, `_indicator_facts`

## Depende de

- [[core.__init__.py]] — importa `card`, `geo`
- [[core.agents_registry.py]] — importa `AGENT_LABEL`, `CALL_ROLE`, `SEAT_AGENT`
- [[core.gpr.py]] — importa `gpr_cached`
- [[core.live_fundamentals.py]] — importa `get_all`
- [[matrix.tensor.py]] — importa `tensor`
- [[research.context.py]] — importa `ContextBuilder`, `render_context`

## Lo usan

- [[core.agents_api.py]] — lo importa
- [[research.ask_agent.py]] — lo importa
- [[research.committee.py]] — lo importa

_Además lo importan 3 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_agents_registry.py]]
- [[tests.test_ask_agent.py]]
- [[tests.test_committee_os_narr.py]]
- [[tests.test_jev_router.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 (b) — LIMPIEZA QUE NO QUEDEN COSAS SUELTAS (sw v254)]]
- [[Sesión 2026-10-09 — EL COMITÉ ENTRA A KHIPUS OS (sw v250)]]
- [[Sesión 2026-10-06 (iii) — HABILIDADES PROPIAS DE CADA AGENTE (sw v247)]]
