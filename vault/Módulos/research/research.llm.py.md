---
tipo: "modulo"
capa: "Investigación"
ruta: "research/llm.py"
lenguaje: "python"
lineas: 302
aliases: ["research/llm.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/llm.py

> Módulo · capa [[Capa Investigación]] · 302 líneas · `research/llm.py`

## Para qué sirve

abstracción de proveedor de modelos (no acoplada a nadie).

## API pública

- `estimate_tokens(text)` _(línea 51)_
- `estimate_cost(model_label, tokens_in, tokens_out)` — USD estimados. R5: UNA sola tabla de precios para todo (core.ai_usage.PRICES + AI_PRICES_JSON): antes research tenía la suya (claude-sonnet … _(línea 65)_
- clase `LLMError` — `meta` (opcional): tokens ya gastados antes de fallar — el presupuesto los cuenta (R5). _(línea 78)_
- clase `LLMProvider` _(línea 86)_
- clase `CoreProvider` — Un proveedor de core/ai.py (claude|gemini|nvidia), sin cascada interna. _(línea 136)_
- clase `FakeProvider` — Para tests: devuelve respuestas guionadas (texto o callable(prompt)). _(línea 173)_
- `route_for(agent_type)` _(línea 208)_
- clase `RoutedProvider` — Cascada de proveedores para UN agente: si uno falla (red, clave, modelo retirado o salida inválida tras reintentos) pasa al siguiente. _(línea 214)_

**Internas** (empiezan con `_`): `_busy_retries`, `_busy_wait_s`, `_sleep`, `_BusyExhausted`, `_meter`, `_parse_route`

## Depende de

- [[core.ai.py]] — importa `AIBusyError`, `_extract_json`, `ai`
- [[core.ai_usage.py]] — importa `cost_of`, `meter`

## Lo usan

- [[research.agents.base.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.debate.py]] — lo importa
- [[research.runner.py]] — lo importa

_Además lo importan 10 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV RESEARCH_BUSY_RETRIES]]
- [[ENV RESEARCH_MODEL_DEFAULT]]
- [[ENV RESEARCH_MODEL_{X}]]

## Pruebas que lo cubren

- [[tests.test_ai_calls.py]]
- [[tests.test_ai_usage_cache.py]]
- [[tests.test_committee_os_narr.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_review_fixes.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_phase3.py]]
- [[tests.test_repair_committee.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_research.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
