---
tipo: "modulo"
capa: "MCP y API"
ruta: "mcp_server/ops.py"
lenguaje: "python"
lineas: 486
aliases: ["mcp_server/ops.py"]
tags: ["capa/mcp-api", "tipo/modulo"]
---

# mcp_server/ops.py

> Módulo · capa [[Capa MCP y API]] · 486 líneas · `mcp_server/ops.py`

## Para qué sirve

las operaciones MCP que faltaban (ARQUITECTURA_V2 §15; BRECHAS L4-09, decisión #15).

## API pública

- `t_run_scenario(ctx, shocks=…, scenario=…, factors=…, top=…, positions=…)` _(línea 70)_
- `t_get_subgraph(ctx, seeds, question=…, depth=…, direction=…, budget_chars=…, include_partners=…, min_confidence=…)` _(línea 157)_
- `t_get_exposure(ctx, positions=…, entity=…)` _(línea 198)_
- `t_find_similar_entities(ctx, id, k=…, space=…)` _(línea 296)_
- `t_get_history(ctx, id_or_ticker, range=…, frequency=…, max_points=…)` _(línea 368)_
- `correlation(a, b, method=…)` — (r, n) de dos listas alineadas; Spearman = Pearson de los rangos. _(línea 401)_
- `corr_matrix(series, method=…, min_obs=…)` — series {símbolo: {fecha: precio}} → (símbolos, matriz r, matriz n, matriz error estándar) con retornos diarios simples sobre las fechas … _(línea 416)_
- `t_calculate_correlation(ctx, symbols, window=…, method=…)` _(línea 455)_

**Internas** (empiezan con `_`): `_graph`, `_kernel`, `_gen_meta`, `_prices`, `_pct_map`, `_symbol_of`, `_series`, `_downsample`, `_ranks`

Define **6 herramientas MCP** → [[API herramientas MCP]]

## Depende de

- [[core.__init__.py]] — importa `_ticker_map`, `account`, `default_kernel`, `hot`, `impact`
- [[core.context_engine.py]] — importa `canon`, `context_engine`
- [[core.entities.py]] — importa `resolve`
- [[core.portfolio_advisor.py]] — importa `_resolve_positions`
- [[core.quotes.py]] — importa `fetch_quotes_live`
- [[core.risk_report.py]] — importa `risk_report`
- [[core.scenario_engine.py]] — importa `scenario_engine`
- [[core.semantic.py]] — importa `semantic`
- [[matrix.tensor.py]] — importa `tensor`
- [[mcp_server.tools.py]] — importa `InvalidParams`, `ToolError`, `_bounded`, `_now_iso`, `_resolve_or_fail`, `tool`

## Lo usan

- [[mcp_server.tools.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_mcp.py]]
