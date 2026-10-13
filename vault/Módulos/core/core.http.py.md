---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/http.py"
lenguaje: "python"
lineas: 189
aliases: ["core/http.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/http.py

> Módulo · capa [[Capa Infraestructura]] · 189 líneas · `core/http.py`

## Para qué sirve

llamadas upstream saneadas y límite de tasa (compartidos entre server, ontology y matrix).

## API pública

- `secret_values(min_len=…, extra=…)` — Valores actuales de las variables secretas (≥ min_len), del más largo al más corto. _(línea 75)_
- `redact_secrets(text, extra=…, limit=…, patterns=…, min_len=…)` — Texto sin secretos: valores exactos de las env de SECRET_ENV_NAMES (+extra) y, con patterns=True, los patrones … _(línea 89)_
- `rate_limit(limit, window=…)` — Decorator: limit calls per IP. limit=max, window=seconds (default 1 hour). IP = último salto de X-Forwarded-For (el del proxy de confianza). _(línea 173)_

**Internas** (empiezan con `_`): `_safe_ticker`, `_safe_get`, `_prune_rate_buckets`, `_rate_limit`, `_client_ip`

## Depende de

- [[core.config.py]] — importa `HTTP_TIMEOUT`
- [[core.pin.py]] — importa `client_ip`

## Lo usan

- [[brokerage.api.py]] — lo importa
- [[brokerage.risk.py]] — lo importa
- [[core.agents_api.py]] — lo importa
- [[core.ai.py]] — lo importa
- [[core.decide_api.py]] — lo importa
- [[core.governance_api.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa
- [[core.ledger_api.py]] — lo importa
- [[core.news_feed.py]] — lo importa
- [[core.ops_check.py]] — lo importa
- [[core.options.py]] — lo importa
- [[core.portfolio_ai.py]] — lo importa
- [[core.portfolio_reports_api.py]] — lo importa
- [[core.prices_api.py]] — lo importa
- [[core.providers.coingecko.py]] — lo importa
- [[core.providers.market.py]] — lo importa
- [[core.providers.news.py]] — lo importa
- [[core.quotes.py]] — lo importa
- [[core.risk_report.py]] — lo importa
- [[core.space.py]] — lo importa
- [[core.world.py]] — lo importa
- [[matrix.api.py]] — lo importa
- [[matrix.tensor_api.py]] — lo importa
- [[mcp_server.api.py]] — lo importa
- [[mcp_server.auth.py]] — lo importa
- [[mcp_server.oauth.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[research.api.py]] — lo importa
- [[research.auto_events.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[research.context.py]] — lo importa
- [[research.outcomes.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 33 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV ALPACA_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV ALPACA_OAUTH_CLIENT_SECRET]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV ALPACA_SECRET]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV ALPHA_VANTAGE_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV ANTHROPIC_API_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV ANTHROPIC_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV AV_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV BROKERAGE_ENC_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV CLAUDE_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV COINGECKO_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV DATABASE_URL]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV ELEVENLABS_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV FINNHUB_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV FINNHUB_WS_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV FMP_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV GEMINI_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV GOOGLE_API_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV KHIPU_ADMIN_SECRET]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV MARKETSTACK_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV MCP_STATIC_TOKEN]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV NVIDIA_API_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV NVIDIA_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV REDIS_URL]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV SECRET_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV TAVILY_API_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV TAVILY_KEY]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV TRADE_PIN]] _(en una lista, p. ej. para tapar secretos en logs)_

## Pruebas que lo cubren

- [[tests.test_brokerage.py]]
- [[tests.test_cierre_infra.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_gates_resulting_state.py]]
- [[tests.test_governance_activation.py]]
- [[tests.test_governance_flow.py]]
- [[tests.test_hot_contract.py]]
- [[tests.test_infra.py]]
- [[tests.test_khipus_os_fixes_server.py]]
- [[tests.test_khipus_os_perf.py]]
- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_core.py]]
- [[tests.test_ledger_privacy.py]]
- [[tests.test_mcp.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_overnight_voice_server.py]]
- [[tests.test_portfolio_ai.py]]
- [[tests.test_providers.py]]
- [[tests.test_reconcile.py]]
- [[tests.test_repair_ontology_review.py]]
- [[tests.test_repair_ops.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_review_batch_g.py]]
- [[tests.test_review_infra_c.py]]
- [[tests.test_security.py]]
- [[tests.test_trading_agent_ledger.py]]
- [[tests.test_voice_tour.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (i) — NEO4J RETIRADO (decisión 6 de Fabrizio) — sw v264]]
- [[Sesión 2026-09-21 — Limpieza estructural - Track A Fase 2 + Track B completos]]
- [[Sesión 2026-08-01 — Prompt frontend+IA (Cowork) - Tracks C y D implementados]]
