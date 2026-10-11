---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "core/khipu_chat.py"
lenguaje: "python"
lineas: 2728
aliases: ["core/khipu_chat.py"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# core/khipu_chat.py

> Módulo · capa [[Capa Chat y agentes]] · 2.728 líneas · `core/khipu_chat.py`

## Para qué sirve

EL cerebro conversacional de Khipu (texto).

## API pública

- `tool_agent(name, args=…)` — Herramienta (+ sus argumentos) → id de la mascota que la "hace". _(línea 129)_
- `valid_req_id(x)` _(línea 153)_
- `progress_begin(req_id)` _(línea 166)_
- `progress_phase(req_id, phase)` _(línea 177)_
- `progress_add(req_id, tool, args=…, state=…)` — Registra una consulta → índice (para actualizar su estado) o None. _(línea 186)_
- `progress_set(req_id, idx, state)` _(línea 198)_
- `progress_end(req_id)` _(línea 215)_
- `progress_get(req_id)` _(línea 230)_
- clase `ChatValidationError` _(línea 245)_
- clase `ToolFailure` — Error de una herramienta propia (se le devuelve al modelo como texto). _(línea 251)_
- `tool_catalog()` — [(nombre, firma, descripción)] de las herramientas DISPONIBLES ahora. _(línea 312)_
- `x_get_news(company, limit=…)` _(línea 345)_
- `x_ask_agent(seat, question, company, lang=…)` _(línea 395)_
- `x_scenario_exposure(scenario)` _(línea 433)_
- `x_market_movers(direction=…, limit=…, sector=…)` _(línea 453)_
- `x_rank_companies(by=…, sector=…, country=…, listed_only=…, limit=…)` _(línea 492)_
- `x_get_space_summary()` _(línea 541)_
- `x_web_search(query)` _(línea 576)_
- `tool_names()` _(línea 590)_
- `execute_tool(name, args, app=…, lang=…)` — → (ok, result_dict). Nunca lanza. `lang` = idioma de la petición: se pasa a las herramientas que redactan en un idioma (ask_agent), por … _(línea 627)_
- `resolve_node(x)` — id/ticker/nombre → id canónico del grafo, o None. _(línea 694)_
- `validate_actions(raw)` _(línea 711)_
- `validate_request(body)` _(línea 795)_
- `build_system(lang, mode=…, agents_enabled=…)` — mode: 'simple' | 'pro' | None (llamadas internas: sin regla de modo). agents_enabled: ids de mascotas activas (None = todas). Ambos vienen … _(línea 916)_
- `build_prompt(message, history, lang, context, scratch, rounds_left, force_final, feedback=…, live=…)` — Orden (2026-10-04): contexto → historial → resultados → PREGUNTA ACTUAL al FINAL → formato. Los modelos pesan el final del prompt: antes la … _(línea 1037)_
- clase `StepParseError` _(línea 1096)_
- `parse_step(text)` — → ('final', {'answer','actions'}) | ('tools', [{'tool','args'}]). Lanza StepParseError. _(línea 1137)_
- `truncated(text)` — ¿La respuesta quedó cortada? (negritas sin cerrar, paréntesis abiertos o termina a mitad de palabra sin puntuación). _(línea 1184)_
- `leaked(text)` — ¿El texto trae restos del protocolo o del "pensamiento en voz alta" del modelo? _(línea 1199)_
- `synthesize(message, history, lang, context, scratch, timeout, tier=…)` — El AGENTE redacta la respuesta final en prosa a partir de lo consultado (cuando el paso con protocolo JSON falló o se acabó el tiempo de … _(línea 1221)_
- `company_summary(c, lang)` _(línea 1283)_
- `fallback_answer(message, lang, reason, results, deadline, app=…, req_id=…)` — Respuesta SIN IA con datos reales. → (answer, actions, extra_results). _(línea 1346)_
- `chat_entities(message, calls, context=…, limit=…)` — [{id, label}] — empresas DETECTADAS en la pregunta (primero, en orden) y las que consultaron las herramientas. Ids canónicos del grafo … _(línea 2026)_
- `chat_cards(calls, entities)` — {company?, committee?} de la empresa PRINCIPAL (la 1.ª detectada) con los resultados ya obtenidos. _(línea 2108)_
- `agents_used(calls, message, context=…, entities=…)` — [{agent, tools, ok, note_es, note_en, source, as_of}] en el orden de las mascotas. La nota se arma SOLO con valores de los resultados (sin … _(línea 2124)_
- `enrich_answer(message, calls, context=…, req_id=…)` — Campos que Khipus OS SUMA a la respuesta (nunca reemplaza ninguno). _(línea 2201)_
- `client_deadline(v)` — `deadline_s` del cuerpo → segundos acotados [15, 120] o None (sin plazo propio = el de siempre). _(línea 2258)_
- `run_chat(message, history=…, lang=…, context=…, app=…, budget_s=…, max_steps=…, req_id=…, deadline_s=…)` — PORTERO (Jev, core/decide.py): decide en paralelo qué necesita la pregunta. En SOMBRA solo se compara con lo que el chat hizo; con … _(línea 2269)_
- `chat_endpoint()` _(línea 2683)_
- `chat_progress_endpoint(req_id)` — Qué agentes están trabajando en la pregunta `req_id` → {req_id, done, elapsed_ms, phase, agents:[{agent, tool, state: … _(línea 2706)_
- `tools_endpoint()` _(línea 2723)_

**Internas** (empiezan con `_`): `_ai_interactive`, `_submit_ai`, `_prog_purge_locked`, `_progress_from_future`, `_now_iso`, `_extra`, `_mcp`, `_principal`, `_schema_sig`, `_clip`, `_snapshot`, `_node_label`, `_research_session`, `_web_available`, `_board_memo_flags`, `_guess_lang`, `_agents_rule`, `_balance_edges`, `_compact_for_chat`, `_fmt_result`, `_args_summary`, `_json_objects`, `_prose_answer`, `_num`, `_entities_in`, `_friendly_source`, `_collect_sources`, `_src_name`, `_fmt_num`, `_pct`, `_usd_b`, `_price`, `_quote`, `_decision_labels`, `_risk_sources`, `_iso_time`, `_session_live`, `_chg_label`, `_price_time`, `_note_company`, `_note_structure`, `_note_supply_chain`, `_note_rank`, `_note_news`, `_note_world`, `_note_web`, `_note_scenario`, `_note_movers`, `_note_risk_report`, `_note_greeks`, `_note_memo`, `_memo_expired`, `_board_committee`, `_board_num`, `_note_board`, `_note_track`, `_note_research`, `_note_ask`, `_note_search`, `_note_health` y 10 más

## Depende de

- [[core.ai.py]] — importa `ai`
- [[core.ai_usage.py]] — importa `ai_usage`
- [[core.config.py]] — importa `FINNHUB`
- [[core.decide.py]] — importa `decide`
- [[core.entities.py]] — importa `resolve`
- [[core.http.py]] — importa `_safe_get`, `_safe_ticker`, `rate_limit`
- [[core.live_caps.py]] — importa `get_caps`
- [[core.live_facts.py]] — importa `detect_entities`, `live_facts_block`
- [[core.scenario_engine.py]] — importa `scenario_engine`
- [[core.semantic.py]] — importa `semantic`
- [[core.space.py]] — importa `space`
- [[core.websearch.py]] — importa `_web_search_available`, `web_search`
- [[core.world.py]] — importa `client_nrs`
- [[mcp_server.auth.py]] — importa `Principal`
- [[mcp_server.tools.py]] — importa `(dinámico: mcp_server.tools)`, `tools`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[research.ask_agent.py]] — importa `ask_agent`, `seat_from_words`
- [[research.committee.py]] — importa `DECISION_LABEL`, `_ttl_hours`, `committee`
- [[research.errors.py]] — importa `friendly`
- [[server.py]] — importa `(dinámico: server)`

## Lo usan

- [[core.agents_api.py]] — lo importa
- [[core.portfolio_reports_api.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 15 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `POST` | `/api/khipu/chat` | `chat_endpoint` | [[core.ai_usage.py]], [[engine.khipu_chat.js]], 3 pruebas |
| `GET` | `/api/khipu/chat/progress/<req_id>` | `chat_progress_endpoint` | [[engine.khipu_chat.js]], 1 prueba |
| `GET` | `/api/khipu/tools` | `tools_endpoint` | 1 prueba |

Grupos: [[API khipu]]

## Pruebas que lo cubren

- [[tests.test_ai_gemini_fast.py]]
- [[tests.test_ask_agent.py]]
- [[tests.test_chat_portfolio_agent.py]]
- [[tests.test_committee_os_narr.py]]
- [[tests.test_decide.py]]
- [[tests.test_jev_router.py]]
- [[tests.test_khipu_chat.py]]
- [[tests.test_khipus_os_chat.py]]
- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_khipus_os_server.py]]
- [[tests.test_overnight_ai_routing.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_repair_review2.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (iii) — HABILIDADES PROPIAS DE CADA AGENTE (sw v247)]]
- [[Sesión 2026-10-04 (g) — KHIPU COMO ASISTENTE - ANALISTAS EN EL CHAT, PROMPT, MEMORIA]]
- [[Sesión 2026-10-03 (e) — RESPUESTAS CORTADAS + HERRAMIENTA DE ESCENARIOS EN EL CHAT]]
- [[Sesión 2026-10-03 (d) — KHIPU YA NO FILTRA SU BORRADOR EL AGENTE REDACTA SIEMPRE]]
- [[Sesión 2026-09-30 al 10-02 — MONITORES, RIESGO FÁCIL, ASISTENTE, CEREBRO DE KHIPU]]
