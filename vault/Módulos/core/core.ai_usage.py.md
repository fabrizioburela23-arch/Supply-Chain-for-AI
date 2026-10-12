---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/ai_usage.py"
lenguaje: "python"
lineas: 553
aliases: ["core/ai_usage.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/ai_usage.py

> Módulo · capa [[Capa Infraestructura]] · 553 líneas · `core/ai_usage.py`

## Para qué sirve

CONTROL DE GASTO DE IA (registro, límites y reporte).

## API pública

- clase `AIBudgetError` — Se alcanzó un límite de gasto: la llamada NO se hace (no cobra). _(línea 89)_
- `price_for(provider, model)` — (entrada, salida) USD por 1M tokens. Prefijo más largo que calce. _(línea 116)_
- `cost_of(provider, model, tin, tout)` _(línea 132)_
- `ai_context(feature=…, who=…)` _(línea 139)_
- `meter()` — Suma los tokens REALES que record() anota en ESTE hilo mientras dura el bloque (incluido el "pensamiento" que el proveedor cobra como … _(línea 152)_
- `current()` _(línea 179)_
- `bind(fn)` — Envuelve fn para que, al correr en OTRO hilo (ThreadPoolExecutor), herede la función/quién del hilo que la creó. _(línea 199)_
- `default_settings()` _(línea 226)_
- `settings()` _(línea 233)_
- `save_settings(values, actor)` _(línea 251)_
- `check(provider, max_tokens=…)` — Antes de cada llamada: ¿se pasó algún límite? → AIBudgetError (no se llama). _(línea 328)_
- `record(provider, model, tin, tout, ok=…, ms=…, estimated=…)` — Después de cada respuesta del proveedor (también las que se descartan: se cobraron igual). _(línea 364)_
- `estimate_tokens(text)` _(línea 387)_
- `flush()` _(línea 392)_
- `report(days=…, lang=…)` _(línea 442)_
- `anthropic_cost_report()` — Costo REAL facturado por Anthropic este mes (Usage & Cost Admin API). Requiere ANTHROPIC_ADMIN_KEY (sk-ant-admin…, solo organizaciones). … _(línea 506)_

**Internas** (empiezan con `_`): `_now`, `_today`, `_prices`, `_meter_add`, `_env_float`, `_add`, `_load_from_db`, `_spent`, `_ensure_writer`, `_agg_db`, `_reset_for_tests`

## Depende de

- [[core.logjson.py]] — importa `current_fields`, `event`, `log_context`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[research.models.py]] — importa `AISetting`, `AIUsage`

## Lo usan

- [[core.ai.py]] — lo importa
- [[core.decide.py]] — lo importa
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

_Además lo importan 10 pruebas (lista abajo)._

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

- [[tests.test_ai_gemini_fast.py]]
- [[tests.test_ai_usage.py]]
- [[tests.test_block0_numbers.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_decide.py]]
- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_overnight_ai_routing.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_repair_logs.py]]
- [[tests.test_repair_research.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
- [[Sesión 2026-10-03 — GASTO DE IA, SIM. ESTRUCTURAL, AVATARES, CANVAS, COMITÉ DE CARTERA]]
