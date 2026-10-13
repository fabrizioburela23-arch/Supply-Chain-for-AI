---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/ai_usage.py"
lenguaje: "python"
lineas: 654
aliases: ["core/ai_usage.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/ai_usage.py

> Módulo · capa [[Capa Infraestructura]] · 654 líneas · `core/ai_usage.py`

## Para qué sirve

CONTROL DE GASTO DE IA (registro, límites y reporte).

## API pública

- clase `AIBudgetError` — Se alcanzó un límite de gasto: la llamada NO se hace (no cobra). _(línea 95)_
- `price_for(provider, model)` — (entrada, salida) USD por 1M tokens. Prefijo más largo que calce. _(línea 143)_
- `cache_price_for(provider, model)` — (escritura, lectura) de caché, USD por 1M tokens (L4-06): los de la fila de PRICES o, si no los trae, los multiplicadores del proveedor … _(línea 148)_
- `cost_of(provider, model, tin, tout, cache_read=…, cache_write=…)` — Costo estimado. `tin` = TODOS los tokens de entrada; `cache_read`/`cache_write` son la parte de ellos que se leyó de / se escribió en la … _(línea 158)_
- `ai_context(feature=…, who=…)` _(línea 173)_
- `meter()` — Suma los tokens REALES que record() anota en ESTE hilo mientras dura el bloque (incluido el "pensamiento" que el proveedor cobra como … _(línea 186)_
- `current()` _(línea 221)_
- `bind(fn)` — Envuelve fn para que, al correr en OTRO hilo (ThreadPoolExecutor), herede la función/quién del hilo que la creó. _(línea 241)_
- `default_settings()` _(línea 279)_
- `settings()` _(línea 286)_
- `save_settings(values, actor)` _(línea 304)_
- `check(provider, max_tokens=…)` — Antes de cada llamada: ¿se pasó algún límite? → AIBudgetError (no se llama). _(línea 386)_
- `record(provider, model, tin, tout, ok=…, ms=…, estimated=…, cache_read=…, cache_write=…)` — Después de cada respuesta del proveedor (también las que se descartan: se cobraron igual). `tin` = TODOS los tokens de entrada; … _(línea 422)_
- `estimate_tokens(text)` _(línea 452)_
- `flush()` _(línea 457)_
- `report(days=…, lang=…)` _(línea 507)_
- `anthropic_cost_report()` — Costo REAL facturado por Anthropic este mes (Usage & Cost Admin API). Requiere ANTHROPIC_ADMIN_KEY (sk-ant-admin…, solo organizaciones). … _(línea 607)_

**Internas** (empiezan con `_`): `_now`, `_today`, `_prices`, `_price_row`, `_meter_add`, `_env_float`, `_add`, `_load_from_db`, `_spent`, `_ensure_writer`, `_agg_db`, `_cache_totals`, `_reset_for_tests`

## Depende de

- [[core.ai_calls.py]] — importa `ai_calls`
- [[core.decision_sites.py]] — importa `decision_sites`
- [[core.logjson.py]] — importa `current_fields`, `event`, `log_context`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[research.models.py]] — importa `AISetting`, `AIUsage`

## Lo usan

- [[core.ai.py]] — lo importa
- [[core.ai_calls.py]] — lo importa
- [[core.decide.py]] — lo importa
- [[core.governance_flow.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa
- [[core.portfolio_advisor.py]] — lo importa
- [[core.portfolio_report.py]] — lo importa
- [[core.portfolio_reports_api.py]] — lo importa
- [[research.ask_agent.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[research.debate.py]] — lo importa
- [[research.health.py]] — lo importa
- [[research.llm.py]] — lo importa
- [[research.runner.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 13 pruebas (lista abajo)._

## Endpoints que llama

- `DELETE /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `GET /api/diagnostics` → [[server.py]] ([[API diagnostics]])
- `GET /api/health` → [[server.py]] ([[API health]])
- `GET /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `OPTIONS /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `POST /api/ai/analyze` → [[server.py]] ([[API ai]])
- `POST /api/khipu/chat` → [[core.khipu_chat.py]] ([[API khipu]])
- `POST /api/sim/agents` → [[server.py]] ([[API sim]])
- `POST /api/thesis/quick` → [[server.py]] ([[API thesis]])
- `POST /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])

## Variables de entorno que lee (solo nombres)

- [[ENV AI_DAILY_LIMIT_USD]]
- [[ENV AI_MONTHLY_LIMIT_USD]]
- [[ENV AI_PER_USER_DAILY_USD]]
- [[ENV AI_PRICES_JSON]]
- [[ENV ANTHROPIC_ADMIN_KEY]]

## Pruebas que lo cubren

- [[tests.test_ai_calls.py]]
- [[tests.test_ai_gemini_fast.py]]
- [[tests.test_ai_usage.py]]
- [[tests.test_ai_usage_cache.py]]
- [[tests.test_block0_numbers.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_decide.py]]
- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_overnight_ai_routing.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_repair_logs.py]]
- [[tests.test_repair_research.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
- [[Sesión 2026-10-03 — GASTO DE IA, SIM. ESTRUCTURAL, AVATARES, CANVAS, COMITÉ DE CARTERA]]
