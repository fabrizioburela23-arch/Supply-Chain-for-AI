---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "matrix/api.py"
lenguaje: "python"
lineas: 964
aliases: ["matrix/api.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# matrix/api.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 964 líneas · `matrix/api.py`

## Para qué sirve

blueprint Flask del motor de matrices: /api/matrix/\*.

## API pública

- `matrix_status()` _(línea 217)_
- `matrix_get(rel_type)` _(línea 255)_
- `matrix_impact()` — Body: {shock: [ids], magnitude?, damping?, max_hops?, rel_weights?, as_of?} → {impacts: {id: pct}, cascade: [{id, hop, impact}], … _(línea 285)_
- `matrix_save_sim()` — Guarda una simulación en la ontología (objeto type='Simulation') → hereda fecha (recorded_at) e historial. Body: {actor, name, targets, … _(línea 358)_
- `matrix_list_sims()` — Historial de simulaciones guardadas, más recientes primero. _(línea 392)_
- `matrix_insights()` — El hipergrafo corre una simulación EN VIVO con los factores activos y la NARRA. Body: {as_of?, tier?='fast', lang?='es', shock?=[ids]}. Sin … _(línea 503)_
- `matrix_insights_history()` — Historial de insights: cómo fue cambiando la lectura de la red. _(línea 734)_
- `matrix_metrics()` — Métricas por nodo (chokepoints, PageRank, ρ). PESADO sin caché (~50 s de CPU con el grafo completo): caché por época+as_of, presupuesto de … _(línea 766)_
- `matrix_factors()` — Track B: detalle COMPLETO de los Factor activos — /status solo expone un conteo de members; el motor cliente (livesim) necesita el dict … _(línea 828)_
- `matrix_factor_fire()` — WHAT-IF de crisis: dispara UN factor a su severity_crisis SIN mutar la ontología (los factores viven LATENTES — severity 1.0 — para no … _(línea 846)_
- `matrix_parity()` — CORTE SEGURO denso↔disperso (spec §"Plan de despliegue seguro"): corre AMBOS motores sobre los MISMOS datos y reporta la discrepancia … _(línea 920)_

**Internas** (empiezan con `_`): `_env_num`, `_BadParam`, `_Busy`, `_heavy_slot`, `_busy_response`, `_budget_response`, `_compute_allowed`, `_num`, `_bad_param`, `_as_of_norm`, `_as_of_error`, `_rel_weights`, `_ttl_get`, `_ttl_set`, `_db`, `_age_days`, `_fallback_insights`, `_narrate_insights`, `_Flight`, `_flight_join`, `_flight_done`, `_insights_build`, `_insights_tier`, `_persist_insight`

## Depende de

- [[core.ai.py]] — importa `_ai_complete`, `_extract_json`
- [[core.http.py]] — importa `_client_ip`, `_rate_limit`, `rate_limit`
- [[core.pin.py]] — importa `check`
- [[matrix.engine.py]] — importa `REL_TYPES`, `_graph_epoch`, `active_factors`, `build_matrices`, `compute_metrics`, `engine`, `fragility`, `modulate` …
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[ontology.models.py]] — importa `InsightSnapshot`, `ObjectRecord`
- [[ontology.service.py]] — importa `_parse_dt`, `apply_event`

## Lo usan

- [[core.screener.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 3 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/matrix/<rel_type>` | `matrix_get` | [[engine.brief.js]], [[engine.cockpit.js]], [[engine.insights.js]], [[engine.khipu_lang.js]], [[engine.livesim.js]], [[engine.voice.js]], [[engine.worldmonitor.js]], [[engine.xray.js]], 4 pruebas |
| `POST` | `/api/matrix/factor/fire` | `matrix_factor_fire` | [[app.html]], [[engine.khipu_lang.js]], 1 prueba |
| `GET` | `/api/matrix/factors` | `matrix_factors` | [[engine.khipu_lang.js]], [[engine.livesim.js]], 1 prueba |
| `POST` | `/api/matrix/impact` | `matrix_impact` | [[engine.worldmonitor.js]], [[engine.xray.js]], 2 pruebas |
| `POST` | `/api/matrix/insights` | `matrix_insights` | [[engine.cockpit.js]], [[engine.voice.js]], 4 pruebas |
| `GET` | `/api/matrix/insights/history` | `matrix_insights_history` | [[engine.insights.js]], 1 prueba |
| `GET` | `/api/matrix/metrics` | `matrix_metrics` | [[engine.brief.js]], [[engine.insights.js]], 2 pruebas |
| `GET` | `/api/matrix/parity` | `matrix_parity` | 1 prueba |
| `GET` | `/api/matrix/simulations` | `matrix_list_sims` | [[engine.livesim.js]], 1 prueba |
| `POST` | `/api/matrix/simulations` | `matrix_save_sim` | [[engine.livesim.js]], 1 prueba |
| `GET` | `/api/matrix/status` | `matrix_status` | [[engine.insights.js]], [[engine.worldmonitor.js]], 1 prueba |

Grupos: [[API matrix]]

## Variables de entorno que lee (solo nombres)

- [[ENV INSIGHTS_INFLIGHT_WAIT_S]]
- [[ENV MATRIX_BUSY_WAIT_S]]
- [[ENV MATRIX_HEAVY_CONCURRENCY]]

## Pruebas que lo cubren

- [[tests.test_infra.py]]
- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_khipus_os_perf.py]]
- [[tests.test_matrix.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (ii) — KHIPUS OS v1 (sw v245)]]
- [[Sesión 2026-07-19 — Motor de matrices DISPERSAS + centralidad]]
- [[Sesión 2026-07-07 — Etapa 3 — Motor de matrices + hiperaristas - NÚCLEO COMPLETO]]
- [[Sesión 2026-07 — Ampliaciones (tras feedback simulaciones muy cerradas, más info)]]
