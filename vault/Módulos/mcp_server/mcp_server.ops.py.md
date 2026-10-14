---
tipo: "modulo"
capa: "MCP y API"
ruta: "mcp_server/ops.py"
lenguaje: "python"
lineas: 772
aliases: ["mcp_server/ops.py"]
tags: ["capa/mcp-api", "tipo/modulo"]
---

# mcp_server/ops.py

> Módulo · capa [[Capa MCP y API]] · 772 líneas · `mcp_server/ops.py`

## Para qué sirve

las operaciones MCP que faltaban (ARQUITECTURA_V2 §15; BRECHAS L4-09, decisión #15).

## API pública

- `t_run_scenario(ctx, shocks=…, scenario=…, factors=…, top=…, positions=…)` _(línea 74)_
- `t_get_subgraph(ctx, seeds, question=…, depth=…, direction=…, budget_chars=…, include_partners=…, min_confidence=…)` _(línea 197)_
- `t_get_exposure(ctx, positions=…, entity=…)` _(línea 238)_
- `t_find_similar_entities(ctx, id, k=…, space=…)` _(línea 336)_
- `t_get_history(ctx, id_or_ticker, range=…, frequency=…, max_points=…)` _(línea 412)_
- `correlation(a, b, method=…)` — (r, n) de dos listas alineadas; Spearman = Pearson de los rangos. _(línea 445)_
- `corr_matrix(series, method=…, min_obs=…)` — series {símbolo: {fecha: precio}} → (símbolos, matriz r, matriz n, matriz error estándar) con retornos diarios simples sobre las fechas … _(línea 460)_
- `t_calculate_correlation(ctx, symbols, window=…, method=…)` _(línea 499)_
- `ewma_zscores(x, lam=…, seed_n=…, demean=…)` — [(i, z_i)] de cada observación contra la desviación EWMA EX-ANTE (estimada solo con lo anterior; RiskMetrics). demean=True: también una … _(línea 541)_
- `t_find_anomalies(ctx, symbols, window=…, lookback_days=…, z_threshold=…)` _(línea 575)_
- `t_project_portfolio(ctx, positions, horizon_days=…, covariance=…, drift=…)` _(línea 688)_

**Internas** (empiezan con `_`): `_graph`, `_kernel`, `_gen_meta`, `_least_hit_rivals`, `_prices`, `_pct_map`, `_symbol_of`, `_series`, `_downsample`, `_ranks`, `_risk_pol`, `_usd_series`

Define **8 herramientas MCP** → [[API herramientas MCP]]

## Depende de

- [[core.__init__.py]] — importa `_ticker_map`, `account`, `default_kernel`, `hot`, `impact`, `rivals`
- [[core.context_engine.py]] — importa `canon`, `context_engine`
- [[core.entities.py]] — importa `resolve`
- [[core.instruments.py]] — importa `major_ccy`
- [[core.live_caps.py]] — importa `get_caps`
- [[core.portfolio_advisor.py]] — importa `_resolve_positions`
- [[core.prices_store.py]] — importa `prices_store`
- [[core.quotes.py]] — importa `_fx_to_usd`, `fetch_quotes_live`
- [[core.risk_models.py]] — importa `risk_models`
- [[core.risk_report.py]] — importa `risk_policy`, `risk_report`
- [[core.scenario_engine.py]] — importa `scenario_engine`
- [[core.scenario_pnl.py]] — importa `scenario_pnl`
- [[core.semantic.py]] — importa `semantic`
- [[matrix.tensor.py]] — importa `tensor`
- [[mcp_server.tools.py]] — importa `InvalidParams`, `ToolError`, `_bounded`, `_now_iso`, `_resolve_or_fail`, `tool`

## Lo usan

- [[mcp_server.tools.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_genui_rivals.py]]
- [[tests.test_lotej_review_fixes.py]]
- [[tests.test_mcp.py]]
