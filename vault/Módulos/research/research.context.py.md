---
tipo: "modulo"
capa: "Investigación"
ruta: "research/context.py"
lenguaje: "python"
lineas: 846
aliases: ["research/context.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/context.py

> Módulo · capa [[Capa Investigación]] · 846 líneas · `research/context.py`

## Para qué sirve

ContextBuilder: NO se manda el grafo entero al LLM.

## API pública

- clase `Candles` — [(ts, cierre AJUSTADO)] + de dónde salió (`source`) y hasta qué día (`as_of`): toda serie servida lo dice. _(línea 118)_
- `price_indicators(series)` — Indicadores deterministas (sin IA) para el TechnicalAgent. _(línea 160)_
- `pooled_fetchers(fetchers=…)` — POOL DE EVIDENCIA de un job (L4-11): los analistas que corren en paralelo sobre la MISMA empresa comparten lo que se trae — cada (fuente, … _(línea 233)_
- `ficha_evidence(node)` — La FICHA INVESTIGADA de la empresa (lotes importados, khipus.company/1): riesgos, hitos, rondas y valuación, estados reportados, posición … _(línea 325)_
- `holdings_lines(entity_id, limit=…)` — Inversiones y alianzas de la empresa (invest / partner): NO son suministro (regla G4a) y por eso no entran en la evidencia del grafo; para … _(línea 387)_
- `graph_version()` — La generación del grafo que usa el armador de contexto (tests/test_ops_single_source.py). _(línea 411)_
- clase `ContextBuilder` _(línea 417)_
- `render_context(ctx)` — Texto para el prompt. El contenido externo va dentro de &lt;data>…&lt;/data>. _(línea 816)_

**Internas** (empiezan con `_`): `_now`, `_clean`, `_fetch_profile`, `_fetch_financials`, `_fetch_news`, `_fetch_company_news`, `_fetch_candles`, `_fetch_web`, `_fetch_sec_filings`, `_fetch_sec_sections`, `_fetch_mcap`, `_ttl`, `_reliability_for_url`, `_fmt_series`, `_txt`, `_first_url`, `_money`, `_names`, `_entity_ids_for`

## Depende de

- [[core.__init__.py]] — importa `hot`
- [[core.company_data.py]] — importa `_get_json`, `get_annual_financials`, `get_live_profile`
- [[core.config.py]] — importa `FINNHUB`
- [[core.context_engine.py]] — importa `context_engine`
- [[core.entities.py]] — importa `entity_ids_for`, `get_index`
- [[core.http.py]] — importa `_safe_get`, `_safe_ticker`
- [[core.prices_store.py]] — importa `prices_store`
- [[core.quotes.py]] — importa `fetch_market_cap_yahoo`
- [[core.sec.py]] — importa `filing_sections`, `latest_filings`
- [[core.websearch.py]] — importa `web_search`
- [[ontology.provenance.py]] — importa `guess_kind`, `source_trust`
- [[ontology.vocabulary.py]] — importa `flow_relation_types`
- [[research.analytics.py]] — importa `fundamental_ratios`, `peer_table`, `technical_indicators`
- [[research.models.py]] — importa `ResearchClaim`

## Lo usan

- [[core.agents_api.py]] — lo importa
- [[research.agent_skills.py]] — lo importa
- [[research.agents.base.py]] — lo importa
- [[research.agents.registry.py]] — lo importa
- [[research.outcomes.py]] — lo importa
- [[research.runner.py]] — lo importa

_Además lo importan 10 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV AV_KEY]]
- [[ENV FMP_KEY]]

## Pruebas que lo cubren

- [[tests.test_ask_agent.py]]
- [[tests.test_block0_review.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_context_engine.py]]
- [[tests.test_khipus_os_server.py]]
- [[tests.test_ops_single_source.py]]
- [[tests.test_repair_committee.py]]
- [[tests.test_research.py]]
- [[tests.test_research_ficha_evidence.py]]
- [[tests.test_rsi_wilder.py]]
- [[tests.test_sec.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (iii) — HABILIDADES PROPIAS DE CADA AGENTE (sw v247)]]
- [[Sesión 2026-10-02 (noche) — ANÁLISIS MÁS PROFUNDO + CONCLUSIONES EN TODAS PARTES (sw v179)]]
