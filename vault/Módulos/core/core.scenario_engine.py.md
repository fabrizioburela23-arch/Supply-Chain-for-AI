---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "core/scenario_engine.py"
lenguaje: "python"
lineas: 526
aliases: ["core/scenario_engine.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# core/scenario_engine.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 526 líneas · `core/scenario_engine.py`

## Para qué sirve

ANÁLISIS ESTRUCTURAL de un escenario (sin IA).

## API pública

- `country_key(raw)` _(línea 109)_
- `detect(scenario)` — {'themes':[...], 'actor':key|None, 'actor_es','actor_en', 'event':str} _(línea 161)_
- `text_search(scenario, snap, limit=…)` — Productores por búsqueda en las fichas del grafo cuando no hay tema conocido. _(línea 178)_
- `kernel_mode()` — kernel.params.scenario_mode: 1.0.0 'legacy' (la BFS propia de abajo: 2 saltos, ×0,7/×0,45, se CONSERVA solo para que 1.0.0 dé los números … _(línea 203)_
- `analyze(scenario, snap, named_ids=…, lang=…)` — Análisis estructural. Devuelve dict con seeds, hit, benefit, impacts (severidad con signo, camino, canal), summary, watch, timeline y meta. _(línea 236)_

**Internas** (empiezan con `_`): `_plain`, `_in_actor`, `_deg_of`, `_w`, `_rel`, `_flow_adj`, `_kernel_propagate`, `_semver`, `_path_back`

## Depende de

- [[core.__init__.py]] — importa `hot`, `impact`
- [[core.governance.py]] — importa `governance`
- [[matrix.engine.py]] — importa `engine`
- [[ontology.vocabulary.py]] — importa `vocabulary`

## Lo usan

- [[core.khipu_chat.py]] — lo importa
- [[core.sim_agents.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_ai_usage.py]]
- [[tests.test_scenario_kernel.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-03 (e) — RESPUESTAS CORTADAS + HERRAMIENTA DE ESCENARIOS EN EL CHAT]]
- [[Sesión 2026-10-03 — GASTO DE IA, SIM. ESTRUCTURAL, AVATARES, CANVAS, COMITÉ DE CARTERA]]
