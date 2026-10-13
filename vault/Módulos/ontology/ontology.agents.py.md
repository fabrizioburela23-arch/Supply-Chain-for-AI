---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/agents.py"
lenguaje: "python"
lineas: 1027
aliases: ["ontology/agents.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/agents.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 1.027 líneas · `ontology/agents.py`

## Para qué sirve

Fase 3: agentes que observan la ontología y PROPONEN Acciones. Nada se ejecuta sin aprobación humana (salvo lo que el usuario marque como auto-aprobable, no implementado aún — todo pasa por la cola).

## API pública

- `server_flow_degree(session, object_id)` — Grado ESTRUCTURAL de un objeto (G4d): número de pares DISTINTOS (source_id, target_id) vigentes unidos por una relación de FLUJO … _(línea 61)_
- clase `CentinelaNRS` _(línea 105)_
- clase `LectorGDELT` _(línea 141)_
- clase `GuardianCartera` _(línea 192)_
- clase `Cartografo` _(línea 245)_
- clase `RadarEmpresas` _(línea 287)_
- clase `TejedorHiperaristas` — Teje HIPERARISTAS: cuando detecta en noticias un golpe SISTÉMICO que toca a VARIAS empresas del grafo a la vez (sanción, escasez de un … _(línea 357)_
- clase `InvestigadorAutonomo` — Dos caminos: manual (endpoint /agents/investigar, SIEMPRE disponible) o reactivo (Annotations recientes de otros agentes — gateado por … _(línea 505)_
- `auto_cycle(session, actor=…)` — run_agents + auto-aprobación de lo seguro. Devuelve qué se aplicó. _(línea 772)_
- `run_agents(session, only=…, max_proposals_per_agent=…)` — Corre observe()+propose() de cada agente habilitado, inserta las propuestas nuevas en `proposed_actions`. Devuelve un resumen por agente. _(línea 827)_
- `brief_matinal(session, hours=…)` — Resumen de lo que pasó en la ontología en las últimas `hours` horas: eventos nuevos, acciones humanas, propuestas de agentes. No requiere … _(línea 877)_
- `evaluate_alert(session, rule, values=…)` — Evalúa UNA regla y devuelve (fired: bool, current_value, detail). `values` = el lote de AlertIndex (core/hotviews/views/alerts.values): NRS … _(línea 948)_
- `check_alerts(session, owner=…)` — Evalúa todas las alertas activas (o las de `owner`), marca last_fired_at en las que dispararon, y devuelve la lista de las que dispararon … _(línea 998)_

**Internas** (empiezan con `_`): `_utcnow`, `_recently_proposed`, `_ai_explain`, `_compute_server_nrs`, `_hot_nrs`, `_slug`, `_gate_prop`, `_get_live_price`

## Depende de

- [[core.__init__.py]] — importa `alerts`, `card`, `core.gates`, `focus`, `report`
- [[core.ai.py]] — importa `_ai_complete`, `_extract_json`
- [[core.config.py]] — importa `FINNHUB`, `INVESTIGADOR_AUTO`, `INVESTIGADOR_AUTO_CUTOFF_HORAS`
- [[core.decision_sites.py]] — importa `alert_fire_due`, `decision_sites`
- [[core.entities.py]] — importa `UMBRAL_BUSQUEDA`, `UMBRAL_ESCRITURA`, `resolve`
- [[core.governance.py]] — importa `governance`
- [[core.identity.py]] — importa `identity`
- [[core.quotes.py]] — importa `_fetch_quote_raw`
- [[core.websearch.py]] — importa `_web_search_available`, `web_search`
- [[core.world.py]] — importa `client_nrs`
- [[ontology.actions.py]] — importa `ACTION_CATALOG`, `execute_action`
- [[ontology.models.py]] — importa `Alert`, `Event`, `LinkRecord`, `ObjectRecord`, `ProposedAction`
- [[ontology.vocabulary.py]] — importa `vocabulary`

## Lo usan

- [[mcp_server.tools.py]] — lo importa
- [[ontology.api.py]] — lo importa
- herramienta MCP `get_company` → [[API herramientas MCP]]

_Además lo importan 14 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_agent_dudosos.py]]
- [[tests.test_cleanup_nrs_parity.py]]
- [[tests.test_docs_facts.py]]
- [[tests.test_gates_resulting_state.py]]
- [[tests.test_governance_seed_parity.py]]
- [[tests.test_hot_invalidation.py]]
- [[tests.test_hot_review_fixes.py]]
- [[tests.test_investigador.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_core.py]]
- [[tests.test_ontology_agents.py]]
- [[tests.test_ontology_alerts.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_review_infra_c.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (aa) — FUNDAMENTALES EN VIVO DE TODO EL GRAFO (sw v234)]]
- [[Sesión 2026-10-05 (y) — NRS ACOTADO + BÚSQUEDA DEL MAPA (sw v232)]]
- [[Sesión 2026-07-05 — Etapa 1 — Limpieza masiva - COMPLETA (4 batches publicados)]]
- [[Sesión 2026-07-07 — Etapa 3 — Motor de matrices + hiperaristas - NÚCLEO COMPLETO]]
- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
