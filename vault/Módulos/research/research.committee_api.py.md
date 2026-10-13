---
tipo: "modulo"
capa: "Comité"
ruta: "research/committee_api.py"
lenguaje: "python"
lineas: 739
aliases: ["research/committee_api.py"]
tags: ["capa/comite", "tipo/modulo"]
---

# research/committee_api.py

> Módulo · capa [[Capa Comité]] · 739 líneas · `research/committee_api.py`

## Para qué sirve

blueprint /api/committee/\* (PHASE 3).

## API pública

- `run()` — Corre el comité (asíncrono: 202 + memo_id). Con client_id exige PIN. `sync: true` (espera la respuesta en el hilo del pedido) SOLO con PIN … _(línea 102)_
- `memo(memo_id)` _(línea 172)_
- `entity(entity_id)` _(línea 206)_
- `approve(memo_id)` _(línea 274)_
- `reject(memo_id)` _(línea 281)_
- `portfolio_committee()` — Comité de CARTERA (core/portfolio_advisor): riesgo medido + perfil + investigación → acciones concretas como consejo. Nunca ejecuta nada. _(línea 288)_
- `portfolio_notes(a, lang=…)` — Análisis del comité de cartera → texto verificado para el cerebro de Khipu (contexto 'portfolio_notes'): KPIs, cada posición, acciones … _(línea 378)_
- `portfolio_fallback(a, lang=…, verdict=…)` — Respuesta SIN IA, solo con el análisis calculado (nunca una lista genérica del mundo). verdict=False (Khipu o un analista): sin la nota de … _(línea 423)_
- `portfolio_card(a)` — Resumen compacto para la tarjeta dentro del chat. _(línea 456)_
- `portfolio_ask()` — El COMITÉ DE CARTERA dentro del chat (pedido 2026-10-05: "/cartera dime si debería reducir…" debía RESPONDER, no abrir una pantalla): mide … _(línea 472)_
- `board_route()` _(línea 588)_
- `board_refresh()` — Encarga investigación para hasta 3 empresas (viejas, pedidas o clave) y la corre EN SERIE en un hilo (una a la vez: respeta el presupuesto … _(línea 608)_
- `track_record()` _(línea 652)_
- `calibration()` _(línea 667)_
- `evaluate()` _(línea 685)_
- `outcomes_recent()` _(línea 702)_
- `clients()` _(línea 722)_

**Internas** (empiezan con `_`): `_unavailable`, `_pin_status`, `_pin_ok`, `_actor`, `_with_schema`, `_run_async`, `_busy`, `_age_s`, `_decide`, `_record_advice`, `_attach_geo`, `_geo_exposure`, `_register_portfolio_analysis`

## Depende de

- [[brokerage.service.py]] — importa `service`
- [[core.ai.py]] — importa `_ai_configured`
- [[core.ai_usage.py]] — importa `ai_context`
- [[core.decision_sites.py]] — importa `decision_sites`
- [[core.entities.py]] — importa `UMBRAL_BUSQUEDA`, `resolve`
- [[core.geosit.py]] — importa `CHOKEPOINTS`, `COUNTRIES`
- [[core.http.py]] — importa `rate_limit`
- [[core.identity.py]] — importa `identity`
- [[core.khipu_chat.py]] — importa `khipu_chat`
- [[core.pin.py]] — importa `pin`
- [[core.portfolio_advisor.py]] — importa `portfolio_advisor`
- [[core.portfolio_reports_api.py]] — importa `_db`, `_owner`
- [[core.world.py]] — importa `_graph`, `entity_geo_risks`
- [[ontology.db.py]] — importa `init_schema`, `ontology_available`, `session_scope`
- [[research.ask_agent.py]] — importa `ROLE`
- [[research.committee.py]] — importa `acquire_run_slot`, `approve_memo`, `board`, `brokerage_service`, `create_placeholder`, `fail_memo`, `get_memo`, `latest_memo` …
- [[research.deliberation.py]] — importa `AGENT_NAMES`
- [[research.models.py]] — importa `PortfolioReport`
- [[research.outcomes.py]] — importa `BUCKETS`, `CAL_METHOD`, `MIN_N`, `calibration_table`, `evaluate_due`, `k_default`, `recent_outcomes`, `snapshots` …
- [[research.runner.py]] — importa `budget_exhausted`, `create_job`, `daily_budget`, `defer_job`, `execute_job_async`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 4 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/committee/board` | `board_route` | [[engine.brief.js]], [[engine.committee.js]], [[engine.oswindows.js]], 3 pruebas |
| `POST` | `/api/committee/board/refresh` | `board_refresh` | [[engine.committee.js]], 2 pruebas |
| `GET` | `/api/committee/calibration` | `calibration` | [[engine.research.js]], 2 pruebas |
| `GET` | `/api/committee/clients` | `clients` | [[engine.committee.js]], 2 pruebas |
| `GET` | `/api/committee/entity/<entity_id>` | `entity` | [[engine.committee.js]], [[engine.oswindows.js]], 3 pruebas |
| `GET` | `/api/committee/memo/<memo_id>` | `memo` | [[engine.committee.js]], [[engine.oswindows.js]], 3 pruebas |
| `POST` | `/api/committee/memo/<memo_id>/approve` | `approve` | [[engine.committee.js]], [[engine.oswindows.js]], 4 pruebas |
| `POST` | `/api/committee/memo/<memo_id>/reject` | `reject` | [[engine.committee.js]], [[engine.oswindows.js]], 2 pruebas |
| `POST` | `/api/committee/outcomes/evaluate` | `evaluate` | [[engine.committee.js]], 1 prueba |
| `GET` | `/api/committee/outcomes/recent` | `outcomes_recent` | [[engine.committee.js]], 1 prueba |
| `POST` | `/api/committee/portfolio` | `portfolio_committee` | [[engine.pfcommittee.js]], 2 pruebas |
| `POST` | `/api/committee/portfolio/ask` | `portfolio_ask` | [[engine.khipu_chat.js]], 1 prueba |
| `POST` | `/api/committee/run` | `run` | [[engine.committee.js]], 1 prueba |
| `GET` | `/api/committee/track-record` | `track_record` | [[engine.committee.js]], [[engine.research.js]], 2 pruebas |

Grupos: [[API committee]]

## Pruebas que lo cubren

- [[tests.test_chat_portfolio_agent.py]]
- [[tests.test_khipus_os_fixes_windows.py]]
- [[tests.test_khipus_os_perf.py]]
- [[tests.test_khipus_os_windows.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_review_fixes.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_overnight_ui_xray_research.py]]
- [[tests.test_phase3.py]]
- [[tests.test_portfolio_persist.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_security.py]]
- [[tests.test_world_feeds.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (q) — COMITÉ DE CARTERA GEOPOLÍTICA EN VIVO (sw v223)]]
- [[Sesión 2026-10-05 (o) — AGENTES CON CHIP EN EL CHAT - EL COMITÉ DE CARTERA RESPONDE AHÍ]]
