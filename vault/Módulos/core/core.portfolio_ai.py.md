---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "core/portfolio_ai.py"
lenguaje: "python"
lineas: 1277
aliases: ["core/portfolio_ai.py"]
tags: ["capa/dinero", "tipo/modulo"]
---

# core/portfolio_ai.py

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 1.277 líneas · `core/portfolio_ai.py`

## Para qué sirve

ASISTENTE DE CARTERAS (💼 Carteras → 🤖 Asistente).

## API pública

- clase `ValidationError` _(línea 160)_
- `nrs(node, degree)` _(línea 258)_
- `sector_label(sec, lang=…)` _(línea 276)_
- `theme_label(key, lang=…)` _(línea 281)_
- `universe()` — Empresas COTIZADAS del grafo aptas para una cartera (ticker válido, no adquirida/fusionada/subsidiaria/cerrada, no pre-IPO). _(línea 288)_
- `themes_list(lang=…)` _(línea 306)_
- `validate_propose(body)` _(línea 332)_
- `common_returns(histories, syms)` — (fechas comunes, {sym: retornos diarios}) sobre los días comunes. _(línea 405)_
- `inverse_vol(vols)` _(línea 413)_
- `risk_parity(cov, syms, iters=…)` — Contribución al riesgo IGUAL por nombre (ERC), iteración multiplicativa. _(línea 419)_
- `apply_caps(w, meta, max_name, max_sector, max_country)` — Topes por nombre, sector y país redistribuyendo el exceso de forma proporcional. Un tope de grupo imposible (p.ej. un solo sector elegido) … _(línea 459)_
- `score(c, prof_w, goal, max_deg, research)` _(línea 514)_
- `research_signal(claims)` — {id: {net ∈ [-1,1], n, neg}} desde claims activos (confianza como peso). _(línea 529)_
- `build_proposals(p, history_fn=…, fx_fn=…, caps=…, claims=…)` — Núcleo DETERMINISTA. `p` = validate_propose(...). Sin IA. _(línea 572)_
- `deterministic_rationale(pf, p, lang)` _(línea 821)_
- `propose(p, history_fn=…, fx_fn=…, caps=…, claims=…, use_ai=…)` _(línea 887)_
- `validate_ask(body)` _(línea 941)_
- `ask(a, history_fn=…, caps=…, claims=…)` _(línea 1118)_
- `themes_endpoint()` _(línea 1225)_
- `propose_endpoint()` _(línea 1237)_
- `ask_endpoint()` _(línea 1261)_

**Internas** (empiezan con `_`): `_now`, `_cache_get`, `_cache_put`, `_key`, `_lang`, `_country`, `_norm`, `_bad`, `_history`, `_fx`, `_live_caps`, `_claims_for`, `_portfolio_report`, `_graph`, `_nodes`, `_as_list`, `_resolve_exclusions`, `_std`, `_cov`, `_waterfill`, `_pick`, `_size_and_measure`, `_risks`, `_ai_rationales`, `_entity_context`, `_pair_stats`, `_portfolio_ctx`, `_portfolio_text`, `_mentioned`, `_glossary`, `_deterministic_answer`

## Depende de

- [[core.ai.py]] — importa `ai`
- [[core.entities.py]] — importa `UMBRAL_ESCRITURA`, `_SNAPSHOT`, `get_index`, `norm`, `resolve`
- [[core.http.py]] — importa `_safe_ticker`, `rate_limit`
- [[core.live_caps.py]] — importa `get_caps`
- [[core.live_facts.py]] — importa `detect_entities`
- [[core.live_fundamentals.py]] — importa `live_margin`
- [[core.quotes.py]] — importa `_fx_to_usd`
- [[core.risk_report.py]] — importa `build_report`, `compute`, `fetch_history`
- [[core.world.py]] — importa `nrs_concentrated`, `nrs_geo`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[ontology.vocabulary.py]] — importa `flow_degree`
- [[research.models.py]] — importa `ResearchClaim`

## Lo usan

- [[core.portfolio_advisor.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `POST` | `/api/portfolio-ai/ask` | `ask_endpoint` | [[engine.portfolios.js]], 1 prueba |
| `POST` | `/api/portfolio-ai/propose` | `propose_endpoint` | [[engine.portfolios.js]], 1 prueba |
| `GET` | `/api/portfolio-ai/themes` | `themes_endpoint` | [[engine.portfolios.js]], 1 prueba |

Grupos: [[API portfolio-ai]]

## Pruebas que lo cubren

- [[tests.test_portfolio_ai.py]]
- [[tests.test_repair_graph.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-30 al 10-02 — MONITORES, RIESGO FÁCIL, ASISTENTE, CEREBRO DE KHIPU]]
