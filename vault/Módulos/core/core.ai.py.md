---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/ai.py"
lenguaje: "python"
lineas: 1196
aliases: ["core/ai.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/ai.py

> Módulo · capa [[Capa Infraestructura]] · 1.196 líneas · `core/ai.py`

## Para qué sirve

cascada multi-proveedor de IA (Claude → Gemini → NVIDIA).

## API pública

- clase `AIBusyError` — Demasiadas llamadas de IA simultáneas: se rechaza en vez de colgar un hilo. _(línea 77)_
- `ai_background(flag=…)` — Marca explícitamente las llamadas de IA de este hilo como de fondo (flag=True) o interactivas (flag=False), p. ej. un hilo que atiende a un … _(línea 100)_
- clase `AICircuitOpen` — El proveedor está en pausa por un error definitivo reciente. _(línea 232)_
- `circuit_open(provider)` — Estado de la pausa del proveedor (dict) o None si está cerrado/vencido. _(línea 270)_
- `ai_circuit_state()` — {proveedor: {open, kind, reason_es/en, seconds_left, until_iso, hits}} para 🩺 y salud. _(línea 288)_
- `provider_available(name)` — Clave presente Y sin pausa activa — lo que debe mirar quien va a LLAMAR. _(línea 299)_
- `last_errors()` _(línea 316)_
- `observe_diag(provider, ok, err_text=…)` — Lo llama el 🩺 cuando hace un ping propio (fuera de _complete_\*). _(línea 343)_
- `claude_thinking_mode(model)` — Cómo se controla el pensamiento en este modelo: 'between_tools' (Sonnet 5.5) · 'always' (Opus ≥ 5.5, Fable, Mythos, Sonnet > 5.5: no se … _(línea 393)_
- `claude_attempts(model, tier=…, max_tokens=…)` — [(kwargs_extra, max_tokens), …] para UN modelo Claude, en orden: el primero es el preferido; los siguientes son más SEGUROS (se usan si la … _(línea 411)_
- `claude_ping_kwargs(model)` — kwargs de pensamiento para un ping de 1 token (🩺) que el modelo ACEPTA: Haiku 4.5 y viejos → disabled; Sonnet 5.5 → between_tools; Opus … _(línea 451)_
- `claude_system(system)` — `system` para messages.create: texto plano si es corto; un bloque con cache_control si es largo. _(línea 467)_
- `gemini_state()` — Para el 🩺 / salud: orden actual de modelos y cuáles están saturados ahora. _(línea 693)_
- `provider_order(tier=…)` — Orden de la cascada para el nivel ('fast'|'deep'). Profundo: AI_ORDER_DEEP > claude,gemini,nvidia (la AI_ORDER vieja se IGNORA a propósito: … _(línea 915)_
- `ai_route_state()` — Para 🩺 / salud / MCP: el orden EFECTIVO por nivel, de dónde sale y qué modelo usa cada uno. _(línea 924)_
- `strip_reasoning(text)` — Quita el "razonamiento oculto" que algunos modelos (NVIDIA/DeepSeek, Qwen…) escriben en &lt;think>…&lt;/think>. Si el bloque quedó sin cerrar (se … _(línea 1154)_

**Internas** (empiezan con `_`): `_env_num`, `_is_background`, `_ai_slot`, `_small`, `_mono`, `_sleep`, `_transient_wait_s`, `_retry_transient`, `_definitive_kind`, `_open_circuit`, `_close_circuit`, `_note_error`, `_guarded`, `_redact`, `_usage`, `_claude_version`, `_status_of`, `_param_rejected`, `_complete_claude`, `_complete_claude_inner`, `_complete_gemini`, `_NetDown`, `_gemini_post`, `_gemini_major`, `_GeminiHTTP`, `_gemini_models`, `_gemini_mark`, `_complete_gemini_inner`, `_gemini_dead`, `_gemini_mark_dead`, `_gemini_once`, `_complete_nvidia`, `_complete_nvidia_inner`, `_ai_configured`, `_parse_order`, `_legacy_order`, `_order_source`, `_nullctx`, `_ai_complete`, `_aicalls`, `_ai_complete_raw`, `_complete_single`, `_cascade`, `_ai_json`, `_extract_json`

## Depende de

- [[core.ai_calls.py]] — importa `ai_calls`
- [[core.ai_usage.py]] — importa `ai_usage`, `current`
- [[core.config.py]] — importa `AI_MODEL_DEEP`, `AI_MODEL_FAST`, `AI_ORDER`, `AI_ORDER_DEEP_DEFAULT`, `AI_ORDER_EXPLICIT`, `AI_ORDER_FAST_DEFAULT`, `CLAUDE`, `GEMINI_FALLBACK_MODEL` …
- [[core.http.py]] — importa `redact_secrets`
- [[core.live_facts.py]] — importa `live_facts_block`
- [[core.numbers.py]] — importa `ESTIMATE_FEATURES`, `KINDS`, `NUMBERS_RULE`, `facts_from_text`, `mark_unsupported`, `unsupported_in`

## Lo usan

- [[core.khipu_chat.py]] — lo importa
- [[core.portfolio_advisor.py]] — lo importa
- [[core.portfolio_ai.py]] — lo importa
- [[core.portfolio_report.py]] — lo importa
- [[core.sim_agents.py]] — lo importa
- [[matrix.api.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[ontology.agents.py]] — lo importa
- [[research.api.py]] — lo importa
- [[research.ask_agent.py]] — lo importa
- [[research.auto_events.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[research.health.py]] — lo importa
- [[research.llm.py]] — lo importa
- [[research.runner.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `run_research` → [[API herramientas MCP]]

_Además lo importan 30 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV AI_BUSY_WAIT_S]]
- [[ENV AI_CIRCUIT_AUTH_S]]
- [[ENV AI_CIRCUIT_CREDIT_S]]
- [[ENV AI_CIRCUIT_MODEL_S]]
- [[ENV AI_CLAUDE_TIMEOUT_DEEP_S]]
- [[ENV AI_CLAUDE_TIMEOUT_S]]
- [[ENV AI_INTERACTIVE_RESERVE]]
- [[ENV AI_MAX_CONCURRENCY]]
- [[ENV AI_ORDER_DEEP]]
- [[ENV AI_ORDER_FAST]]
- [[ENV AI_TRANSIENT_BASE_S]]
- [[ENV AI_TRANSIENT_CAP_S]]
- [[ENV AI_TRANSIENT_RETRIES]]
- [[ENV GEMINI_HOT_S]]
- [[ENV GEMINI_THINKING]]

## Pruebas que lo cubren

- [[tests.conftest.py]]
- [[tests.test_agent_dudosos.py]]
- [[tests.test_ai_calls.py]]
- [[tests.test_ai_gemini_fast.py]]
- [[tests.test_ai_json.py]]
- [[tests.test_ai_usage.py]]
- [[tests.test_block0_numbers.py]]
- [[tests.test_block0_review.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_context_engine.py]]
- [[tests.test_genui_contract.py]]
- [[tests.test_genui_ledger.py]]
- [[tests.test_infra.py]]
- [[tests.test_jev_router.py]]
- [[tests.test_khipu_chat.py]]
- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_khipus_os_server.py]]
- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_ledger_review_fixes.py]]
- [[tests.test_mcp.py]]
- [[tests.test_numbers_guard.py]]
- [[tests.test_overnight3_diag_bilingual.py]]
- [[tests.test_overnight_ai_routing.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_phase3.py]]
- [[tests.test_portfolio_ai.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_research.py]]
- [[tests.test_scenario_kernel.py]]
- [[tests.test_sim_agents.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-10-04 (g) — KHIPU COMO ASISTENTE - ANALISTAS EN EL CHAT, PROMPT, MEMORIA]]
- [[Sesión 2026-10-04 (f) — EXPECTING VALUE EN INVESTIGAR - JSON ESTRICTO + MENSAJES PARA]]
- [[Sesión 2026-10-03 (e) — RESPUESTAS CORTADAS + HERRAMIENTA DE ESCENARIOS EN EL CHAT]]
- [[Sesión 2026-10-03 — GASTO DE IA, SIM. ESTRUCTURAL, AVATARES, CANVAS, COMITÉ DE CARTERA]]
- [[Sesión 2026-09-28 (e) — PHASE 2 - AGENT RESEARCH SWARM (sw v153)]]
- [[Sesión 2026-07-12 — Etapas I+J — Feedback 8 + Expediente Cripto (sw v76)]]
