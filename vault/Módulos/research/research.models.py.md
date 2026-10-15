---
tipo: "modulo"
capa: "Investigación"
ruta: "research/models.py"
lenguaje: "python"
lineas: 404
aliases: ["research/models.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/models.py

> Módulo · capa [[Capa Investigación]] · 404 líneas · `research/models.py`

## Para qué sirve

tablas de la capa DERIVED CLAIMS (Phase 2).

## API pública

- clase `ResearchClaim` — Conclusión DERIVADA de un agente sobre una entidad. _(línea 25)_
- clase `ResearchEvidence` — Evidencia de una claim — a favor (supporting) o en contra (counter). Apunta a una Source de la ontología (source_id) cuando hay URL, o a … _(línea 68)_
- clase `ClaimRelation` — Relación entre claims. Phase 2 solo crea POTENTIALLY_CONTRADICTS: se DETECTA la tensión, no se decide quién tiene razón (eso es Phase 3). _(línea 90)_
- clase `AgentRun` — Observabilidad: UNA ejecución de UN agente. Permite responder "¿por qué el sistema llegó a esta conclusión?" — con qué modelo, por qué se … _(línea 104)_
- `open_questions_of(run)` — Preguntas abiertas de un AgentRun: la columna nueva + las que las filas viejas guardaban como dict dentro de `errors`. _(línea 138)_
- `errors_of(run)` — Solo los errores de verdad (textos) de un AgentRun — sin las preguntas abiertas viejas. _(línea 148)_
- clase `ResearchJob` — Un pedido de investigación (del usuario o de un evento) sobre una entidad. _(línea 153)_
- clase `ClaimBaseline` — Foto de partida de una claim (una por claim): con qué precio y en qué fecha se hizo la predicción, contra qué referencia (SPY) y cuándo se … _(línea 183)_
- clase `ClaimOutcome` — UNA evaluación de UN checkpoint de una claim (append-only, idempotente por (claim_id, checkpoint)). Guarda los precios usados y la cuenta. _(línea 213)_
- clase `CalibrationSnapshot` — Foto periódica del historial (track record) por agente — para ver cómo evoluciona la calibración en el tiempo. agent_type NULL = global. _(línea 252)_
- clase `CommitteeMemo` — Memo del COMITÉ DE INVERSIÓN automatizado: decisión propuesta + tamaño (determinista) + tesis/riesgos/disenso (presidente IA o plantilla … _(línea 269)_
- clase `DecisionShadow` — JEV (core/decide.py) en MODO SOMBRA: lo que decidió vs lo que hizo el sistema, para medir acuerdo antes de darle control por función. _(línea 312)_
- clase `AIUsage` _(línea 326)_
- clase `AISetting` _(línea 346)_
- clase `PortfolioWatch` _(línea 361)_
- clase `PortfolioReport` _(línea 380)_
- clase `UserState` — Sincronización entre dispositivos (2026-10-03): carteras, perfil y posiciones del usuario, por dueño (hash de la llave del navegador). … _(línea 396)_

**Internas** (empiezan con `_`): `_uuid`

## Depende de

- [[ontology.models.py]] — importa `Base`

## Lo usan

- [[core.agents_api.py]] — lo importa
- [[core.ai_usage.py]] — lo importa
- [[core.decide.py]] — lo importa
- [[core.decision_sites.py]] — lo importa
- [[core.portfolio_ai.py]] — lo importa
- [[core.portfolio_reports_api.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[ontology.db.py]] — lo importa
- [[research.api.py]] — lo importa
- [[research.ask_agent.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[research.context.py]] — lo importa
- [[research.contradictions.py]] — lo importa
- [[research.falsifiers.py]] — lo importa
- [[research.health.py]] — lo importa
- [[research.outcomes.py]] — lo importa
- [[research.router.py]] — lo importa
- [[research.runner.py]] — lo importa
- [[research.schemas.py]] — lo importa
- herramienta MCP `get_claim_evidence` → [[API herramientas MCP]]
- herramienta MCP `get_research` → [[API herramientas MCP]]
- herramienta MCP `get_research_job` → [[API herramientas MCP]]

_Además lo importan 31 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_ai_calls.py]]
- [[tests.test_brokerage.py]]
- [[tests.test_catalog_api_pg.py]]
- [[tests.test_cierre_infra.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_committee_os_narr.py]]
- [[tests.test_genui_ledger.py]]
- [[tests.test_import_lote2_e2e.py]]
- [[tests.test_import_panel.py]]
- [[tests.test_import_roundtrip.py]]
- [[tests.test_infra.py]]
- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_ledger_callsites.py]]
- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_guard.py]]
- [[tests.test_ledger_review_fixes.py]]
- [[tests.test_live_universe_db.py]]
- [[tests.test_mcp.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_phase3.py]]
- [[tests.test_repair_committee.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_repair_ops.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_research.py]]
- [[tests.test_rutas_acceso_decision.py]]
- [[tests.test_trading_agent_ledger.py]]
- [[tests.test_voice_agent_split.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-03 (b) — REPORTES DE CARTERA, PREGÚNTALE A TU CARTERA, NOTICIAS DE TU]]
