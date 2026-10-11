---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/live_facts.py"
lenguaje: "python"
lineas: 204
aliases: ["core/live_facts.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/live_facts.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 204 líneas · `core/live_facts.py`

## Para qué sirve

DATOS EN VIVO para toda llamada de IA.

## API pública

- `detect_entities(text, limit=…)` — Ids del grafo mencionados en `text`, en orden de aparición. _(línea 110)_
- `live_facts_block(text)` — Bloque de texto para anexar al prompt, o '' si no aplica/falla. _(línea 178)_

**Internas** (empiezan con `_`): `_label_regex`, `_collapse`, `_collapsed_map`, `_fuzzy_hits`, `_fact_for`

## Depende de

- [[core.company_data.py]] — importa `get_live_profile`
- [[core.entities.py]] — importa `get_index`
- [[core.quotes.py]] — importa `fetch_market_cap_yahoo`

## Lo usan

- [[core.ai.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa
- [[core.portfolio_ai.py]] — lo importa
- [[core.sim_agents.py]] — lo importa
- [[research.committee.py]] — lo importa

_Además lo importan 5 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_ask_agent.py]]
- [[tests.test_jev_router.py]]
- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_khipus_os_server.py]]
- [[tests.test_live_facts_entities.py]]
- [[tests.test_numbers_guard.py]]
- [[tests.test_overnight_ai_routing.py]]
- [[tests.test_overnight_fixes_review.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (iii) — HABILIDADES PROPIAS DE CADA AGENTE (sw v247)]]
- [[Sesión 2026-09-28 (e) — PHASE 2 - AGENT RESEARCH SWARM (sw v153)]]
