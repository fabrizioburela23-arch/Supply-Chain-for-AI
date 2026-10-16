---
tipo: "modulo"
capa: "Comité"
ruta: "core/portfolio_advisor.py"
lenguaje: "python"
lineas: 541
aliases: ["core/portfolio_advisor.py"]
tags: ["capa/comite", "tipo/modulo"]
---

# core/portfolio_advisor.py

> Módulo · capa [[Capa Comité]] · 541 líneas · `core/portfolio_advisor.py`

## Para qué sirve

COMITÉ DE CARTERA: analiza una cartera completa y da ACCIONES CONCRETAS como consejo (reducir, vender, añadir, diversificar).

## API pública

- `analyze(positions, profile=…, lang=…, risk_fn=…, board_fn=…, cash_usd=…)` — Devuelve el análisis completo (sin IA). risk_fn/board_fn inyectables (tests). _(línea 105)_
- `explain(analysis, lang=…)` — Explicación en lenguaje simple (IA, con guardián de cifras) o determinista. _(línea 327)_
- `plan(analysis, lang=…, today=…)` — analyze() → plan de 3-5 movimientos con antes/después, qué vigilar y cuándo revisar. Puro (sin red ni IA). _(línea 433)_

**Internas** (empiezan con `_`): `_f`, `_resolve_positions`, `_board_index`, `_sector_label`, `_shape`

## Depende de

- [[core.ai.py]] — importa `ai`
- [[core.ai_usage.py]] — importa `ai_context`
- [[core.entities.py]] — importa `resolve`
- [[core.portfolio_ai.py]] — importa `sector_label`
- [[core.risk_report.py]] — importa `build_report`
- [[core.semantic.py]] — importa `_load_snapshot`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[research.committee.py]] — importa `board`

## Lo usan

- [[core.impls.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa
- [[core.portfolio_report.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- herramienta MCP `get_exposure` → [[API herramientas MCP]]

_Además lo importan 5 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_block0_committee.py]]
- [[tests.test_chat_portfolio_agent.py]]
- [[tests.test_ia_concreta_plan.py]]
- [[tests.test_portfolio_advisor.py]]
- [[tests.test_portfolio_persist.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
- [[Sesión 2026-10-05 (m) — EL COMITÉ ANALIZA TODAS LAS POSICIONES (sw v215)]]
- [[Sesión 2026-10-03 — GASTO DE IA, SIM. ESTRUCTURAL, AVATARES, CANVAS, COMITÉ DE CARTERA]]
