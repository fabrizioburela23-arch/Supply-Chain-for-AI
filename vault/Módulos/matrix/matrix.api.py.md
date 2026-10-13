---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "matrix/api.py"
lenguaje: "python"
lineas: 1199
aliases: ["matrix/api.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# matrix/api.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 1.199 líneas · `matrix/api.py`

## Para qué sirve

blueprint Flask del motor de matrices: /api/matrix/\*.

## API pública

- `ledger_whatif(kind, params, impacts, g=…, extra=…)` — Ficha `whatif.shock` / `whatif.factor_fire` (paso 20, §2.5; GV-10): un qué-pasaría-si que la persona LANZÓ (botón, comando, chat — no al … _(línea 284)_
- `matrix_status()` _(línea 315)_
- `matrix_get(rel_type)` _(línea 364)_
- `matrix_impact()` — Body: {shock: [ids], magnitude?, damping?, max_hops?, rel_weights?, as_of?} → {impacts: {id: pct}, cascade: [{id, hop, impact}], … _(línea 394)_
- `matrix_save_sim()` — Guarda una simulación en la ontología (objeto type='Simulation') → hereda fecha (recorded_at) e historial. Body: {actor, name, targets, … _(línea 484)_
- `matrix_list_sims()` — Historial de simulaciones guardadas, más recientes primero. _(línea 523)_
- `matrix_insights()` — El hipergrafo corre una simulación EN VIVO con los factores activos y la NARRA. Body: {as_of?, tier?='fast', lang?='es', shock?=[ids]}. Sin … _(línea 634)_
- `ledger_insight(snap_id, graph_key, lang, payload, ledger=…, persisted=…)` — Ficha `insight.snapshot` (paso 20, async): UNA por fila nueva del historial (ya deduplicado por (versión del grafo + release, as_of, lang), … _(línea 898)_
- `matrix_insights_history()` — Historial de insights: cómo fue cambiando la lectura de la red. _(línea 930)_
- `matrix_metrics()` — Métricas por nodo (chokepoints, PageRank, ρ). PESADO sin caché (~50 s de CPU con el grafo completo): caché por época+as_of, presupuesto de … _(línea 962)_
- `matrix_factors()` — Track B: detalle COMPLETO de los Factor activos — /status solo expone un conteo de members; el motor cliente (livesim) necesita el dict … _(línea 1031)_
- `matrix_factor_fire()` — WHAT-IF de crisis: dispara UN factor a su severity_crisis SIN mutar la ontología (los factores viven LATENTES — severity 1.0 — para no … _(línea 1053)_
- `matrix_parity()` — CORTE SEGURO denso↔disperso (spec §"Plan de despliegue seguro"): corre AMBOS motores sobre los MISMOS datos y reporta la discrepancia … _(línea 1155)_

**Internas** (empiezan con `_`): `_kdef`, `_magnitude_max`, `_env_num`, `_BadParam`, `_Busy`, `_heavy_slot`, `_busy_response`, `_budget_response`, `_compute_allowed`, `_num`, `_bad_param`, `_as_of_norm`, `_as_of_error`, `_rel_weights`, `_ttl_get`, `_ttl_set`, `_db`, `_hot`, `_view_meta`, `_with_view`, `_age_days`, `_fallback_insights`, `_narrate_insights`, `_Flight`, `_flight_join`, `_flight_done`, `_insights_build`, `_insights_tier`, `_persist_insight`

## Depende de

- [[core.__init__.py]] — importa `builder`, `impact`, `registry`, `signals`
- [[core.ai.py]] — importa `_ai_complete`, `_extract_json`
- [[core.ai_calls.py]] — importa `ai_calls`
- [[core.decisions.py]] — importa `decisions`
- [[core.http.py]] — importa `_client_ip`, `_rate_limit`, `rate_limit`
- [[core.identity.py]] — importa `identity`
- [[core.pin.py]] — importa `check`
- [[matrix.engine.py]] — importa `REL_TYPES`, `active_factors`, `build_matrices`, `compute_metrics`, `engine`, `fragility`, `graph_key`, `modulate` …
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[ontology.models.py]] — importa `InsightSnapshot`, `ObjectRecord`
- [[ontology.service.py]] — importa `_parse_dt`, `apply_event`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 8 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/matrix/<rel_type>` | `matrix_get` | [[engine.cockpit.js]], [[engine.khipu_lang.js]], [[engine.livesim.js]], [[engine.voice.js]], [[engine.worldmonitor.js]], 10 pruebas |
| `POST` | `/api/matrix/factor/fire` | `matrix_factor_fire` | [[app.html]], [[engine.khipu_lang.js]], 3 pruebas |
| `GET` | `/api/matrix/factors` | `matrix_factors` | [[engine.khipu_lang.js]], 5 pruebas |
| `POST` | `/api/matrix/impact` | `matrix_impact` | [[engine.worldmonitor.js]], 5 pruebas |
| `POST` | `/api/matrix/insights` | `matrix_insights` | [[engine.cockpit.js]], [[engine.voice.js]], 4 pruebas |
| `GET` | `/api/matrix/insights/history` | `matrix_insights_history` | [[engine.insights.js]], 1 prueba |
| `GET` | `/api/matrix/metrics` | `matrix_metrics` | 6 pruebas |
| `GET` | `/api/matrix/parity` | `matrix_parity` | 1 prueba |
| `GET` | `/api/matrix/simulations` | `matrix_list_sims` | [[engine.livesim.js]], 2 pruebas |
| `POST` | `/api/matrix/simulations` | `matrix_save_sim` | [[engine.livesim.js]], 2 pruebas |
| `GET` | `/api/matrix/status` | `matrix_status` | [[engine.worldmonitor.js]], 3 pruebas |

Grupos: [[API matrix]]

## Endpoints que llama

- `GET /api/matrix/<rel_type>` → [[matrix.api.py]] ([[API matrix]])
- `POST /api/matrix/factor/fire` → [[matrix.api.py]] ([[API matrix]])
- `POST /api/matrix/impact` → [[matrix.api.py]] ([[API matrix]])

## Variables de entorno que lee (solo nombres)

- [[ENV HOTVIEWS]]
- [[ENV HOT_WAIT_S]]
- [[ENV INSIGHTS_INFLIGHT_WAIT_S]]
- [[ENV MATRIX_BUSY_WAIT_S]]
- [[ENV MATRIX_HEAVY_CONCURRENCY]]

## Pruebas que lo cubren

- [[tests.test_hot_contract.py]]
- [[tests.test_hot_invalidation.py]]
- [[tests.test_hot_review_fixes.py]]
- [[tests.test_hot_views_parity.py]]
- [[tests.test_infra.py]]
- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_khipus_os_perf.py]]
- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_matrix.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_ops_graph_version.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_ops_single_source.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (ii) — KHIPUS OS v1 (sw v245)]]
- [[Sesión 2026-07-19 — Motor de matrices DISPERSAS + centralidad]]
- [[Sesión 2026-07-07 — Etapa 3 — Motor de matrices + hiperaristas - NÚCLEO COMPLETO]]
- [[Sesión 2026-07 — Ampliaciones (tras feedback simulaciones muy cerradas, más info)]]
