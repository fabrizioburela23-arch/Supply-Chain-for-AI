---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "core/sim_agents.py"
lenguaje: "python"
lineas: 646
aliases: ["core/sim_agents.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# core/sim_agents.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 646 líneas · `core/sim_agents.py`

## Para qué sirve

Motor de simulación POR AGENTES (interno).

## API pública

- `run(scenario, seeds, lang=…)` — Simula un escenario por agentes. Firma EXACTA: run(scenario, seeds, lang). _(línea 514)_

**Internas** (empiezan con `_`): `_es`, `_sectors9`, `_sector_label`, `_size_class`, `_approx_nrs`, `_neighbors`, `_mentioned`, `_inside_word`, `_seed_ids`, `_no_seeds`, `_build_company_agents`, `_cast_edges`, `_sector_agents`, `_external_agents`, `_clamp_pct`, `_stance_from_pct`, `_system`, `_round_prompt`, `_synth_narrative`, `_default_event`, `_struct_pct`, `_struct_impacts`, `_struct_extras`, `_struct_narrative`, `_fallback`, `_fallback_basic`, `_roster`, `_cast_from_analysis`, `_run_impl`

## Depende de

- [[core.__init__.py]] — importa `hot`
- [[core.ai.py]] — importa `ai`
- [[core.live_facts.py]] — importa `detect_entities`
- [[core.scenario_engine.py]] — importa `scenario_engine`
- [[core.semantic.py]] — importa `semantic`
- [[core.world.py]] — importa `client_nrs`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 4 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_ai_usage.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_ops_single_source.py]]
- [[tests.test_sim_agents.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-03 — GASTO DE IA, SIM. ESTRUCTURAL, AVATARES, CANVAS, COMITÉ DE CARTERA]]
- [[Sesión 2026-09-21 — Limpieza estructural - Track A Fase 2 + Track B completos]]
- [[Sesión 2026-07-13 — Etapa O — Khipus Finance AI - 9 frentes + rebrand + Cabina inicial]]
