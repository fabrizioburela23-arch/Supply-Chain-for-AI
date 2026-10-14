---
tipo: "modulo"
capa: "Infraestructura"
ruta: "server.py"
lenguaje: "python"
lineas: 4903
aliases: ["server.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# server.py

> Módulo · capa [[Capa Infraestructura]] · 4.903 líneas · `server.py`

## Para qué sirve

Khipu Finance v1 Backend proxy ligero para el ecosistema de inteligencia de inversión.

## API pública

- `screener_growth()` — Ranking de señales de crecimiento explosivo sobre TODO el universo cotizable del grafo (~410 símbolos, multi-bolsa). Momentum 5/20/60d + … _(línea 296)_
- `index()` _(línea 697)_
- `service_worker()` _(línea 706)_
- `manifest()` _(línea 724)_
- `icon()` _(línea 742)_
- `serve_nodes(filename)` _(línea 765)_
- `serve_engine(filename)` _(línea 771)_
- `serve_sim(filename)` _(línea 777)_
- `vendor(name)` _(línea 804)_
- `api_vocabulary()` — REGISTRO ÚNICO del vocabulario (tipos de objeto, tipos de relación con su criticidad, tipos de fuente). El cliente debe consumir ESTO en … _(línea 829)_
- `api_vocabulary_unknown()` — Diagnóstico: valores vistos que NO están en el registro. La regla del proyecto es que nada se clasifique en silencio; si algo aparece aquí, … _(línea 855)_
- `health()` _(línea 897)_
- `ai_debug()` — Depuración: ejecuta _ai_complete con un prompt real (tier configurable) y reporta AI_ORDER, los modelos resueltos y el error/modelo real — … _(línea 1683)_
- `diagnostics()` _(línea 1757)_
- `ws_token()` — Token corto (20 s, atado a la IP, un solo uso) para canjear por la key del WebSocket en /api/ws-key. Solo desde el mismo origen. _(línea 1961)_
- `ws_key()` — Valida el session_token (fresco, misma IP, no usado) y devuelve la key del WebSocket: FINNHUB_WS_KEY si existe (recomendado), si no … _(línea 1978)_
- `quote(ticker)` — Cotización de UN ticker por la MISMA cascada que /api/quotes/live (Finnhub→Yahoo, también EE.UU.; Yahoo no necesita key). Devuelve el … _(línea 2040)_
- `market_quote(symbol)` _(línea 2069)_
- `market_providers()` — Qué proveedores hay, cuáles están configurados y por qué no los que no. Honestidad de fuentes (spec §13): nada de fingir integraciones … _(línea 2086)_
- `scalp_price(symbol)` — Precio spot RÁPIDO para el scalping. Acciones → Finnhub (c/pc); cripto (par con '/') → datos de Alpaca (misma key). Caché 2s: fresco para … _(línea 2106)_
- `batch_quotes()` — Varios tickers (?symbols=A,B o ?tickers=A,B) por la MISMA cascada que /api/quotes/live. Mapa plano {T: fila + {c, pc, dp, t} crudos} — … _(línea 2138)_
- `fin_dossier(ticker)` — Series anuales para el dossier financiero de una empresa (lo consumen engine/fincard.js, cockpit.js, termdata.js y localcharts.js): … _(línea 2160)_
- `candles(ticker)` — OHLCV candles for charting, HONRANDO el timeframe (range/interval). _(línea 2188)_
- `trade_account()` _(línea 2514)_
- `trade_status()` — Diagnóstico PÚBLICO no sensible del bróker (sin PIN): NO expone claves ni datos de cuenta — solo si están configuradas, la base y el status … _(línea 2539)_
- `trade_diag()` — Diagnóstico del broker Alpaca — SIN exponer claves. Prueba cada llamada (cuenta, posiciones, órdenes, activos cripto, reloj) y devuelve … _(línea 2625)_
- `trade_crypto_assets()` — Activos cripto tradeables en Alpaca → {"assets":[{symbol,name}], "paper":bool}. _(línea 2721)_
- `trade_close()` — Cierra por completo UNA posición (1-clic 'CLOSE' del scalping) por el camino único: una orden de mercado por TODA la cantidad … _(línea 2862)_
- `trade_order()` — Orden de la cuenta de la casa por el camino ÚNICO (brokerage.service.house_order). Aquí solo se valida la FORMA del pedido (auditoría … _(línea 2915)_
- `company_news(ticker)` _(línea 3031)_
- `crypto_markets()` _(línea 3052)_
- `crypto_detail(coin_id)` _(línea 3068)_
- `crypto_history(coin_id)` _(línea 3082)_
- `crypto_analyze()` — {id?, symbol?, lang, intel?} → análisis CAUTO. Contexto: precio/mercado en vivo (CoinGecko) + ficha estática opcional del cliente. Cache 10 … _(línea 3121)_
- `thesis_quick()` — {id, lang} → informe estructurado que va MÁS ALLÁ de la empresa: sector, competidores, geopolítica, chokepoints de su cadena y una tesis. … _(línea 3209)_
- `ai_usage_report()` _(línea 3283)_
- `ai_usage_limits()` _(línea 3300)_
- `sim_agents_route()` _(línea 3323)_
- `earnings(ticker)` _(línea 3357)_
- `fundamentals(ticker)` _(línea 3378)_
- `insiders(ticker)` _(línea 3462)_
- `ai_analyze()` _(línea 3481)_
- `canvas_generate()` _(línea 3564)_
- `marketstack_proxy()` _(línea 3677)_
- `ipo_calendar()` — IPO calendar from Finnhub — last 90 days + next 30 days _(línea 3694)_
- `space_launches()` — Próximos lanzamientos espaciales, mapeados a nodos de Khipu. Blindado para la demo: timeout corto + respaldo vacío si Launch Library está … _(línea 3716)_
- `space_tle()` — Satélites reales por constelación (CelesTrak). Muestrea para rendimiento pero reporta los conteos REALES (con `as_of`; `stale` = copia de … _(línea 3769)_
- `news_gdelt(company_name)` _(línea 3820)_
- `dossier(ticker)` — Dossier de 5-6 años para la pestaña Análisis (app.html `_dossierRenderPanels`): ingresos, dilución, FCF, valuación, balance, márgenes, … _(línea 3873)_
- `market_live_caps()` — Capitalización + precio EN VIVO de TODAS las cotizadas del grafo (lote Yahoo, caché 15 min, refresco en segundo plano). El cliente pisa con … _(línea 3898)_
- `market_live_fundamentals()` — Fundamentales EN VIVO (margen, crecimiento, ingresos 12 m, empleados) de todas las cotizadas, refrescados por tandas en segundo plano … _(línea 3908)_
- `company_live(ticker)` — Perfil EN VIVO de cualquier empresa cotizada (pedido 2026-09-28: "que la info se actualice en vivo"): precio y % del día, capitalización en … _(línea 3917)_
- `company_valuation_news(name)` — Valuación de una PRIVADA según los titulares recientes (GDELT): la cifra citada, medio, fecha y si es ronda cerrada o negociación. Pedido … _(línea 3939)_
- `company_research(ticker)` — Descarga el 10-K/20-F más reciente de SEC EDGAR y Claude lo sintetiza. _(línea 3997)_
- `grafo_estado()` _(línea 4060)_
- `deep_analyze()` — Arranca una investigación profunda (Capa 4). Una a la vez por worker. _(línea 4168)_
- `client_diag()` _(línea 4217)_
- `client_diag_recent()` _(línea 4236)_
- `deep_status()` _(línea 4257)_
- `portfolio_risk_report()` — REPORTE DE RIESGO (VaR/CVaR/volatilidad/beta/correlaciones/contribución) con precios diarios REALES de 1 año. Body: {positions:[{symbol, … _(línea 4321)_
- `portfolio_vega_report()` — REPORTE VEGA (Kappa) de opciones: griegas Black-Scholes con volatilidad implícita EN VIVO del contrato. Body: {options:[{symbol, kind, … _(línea 4343)_
- `options_chain(symbol)` — Vencimientos y strikes disponibles del subyacente (selectores de la UI). _(línea 4361)_
- `api_portfolio_risk_internal()` — VaR + CVaR del portfolio — endpoint interno sin JWT (para uso del browser). _(línea 4373)_
- `generate_khipu_key(user_id, tier=…)` _(línea 4393)_
- `validate_khipu_key(key)` _(línea 4398)_
- `khipu_auth(min_tier=…)` _(línea 4407)_
- `api_issue_key()` — Issue a Khipu Finance API key. Body: {user_id, tier}. Tiers: free/starter/pro/business/enterprise. _(línea 4429)_
- `api_docs()` _(línea 4449)_
- `api_nodes()` _(línea 4471)_
- `api_node_live(node_id)` _(línea 4477)_
- `api_portfolio_risk()` — VaR + CVaR del portfolio del cliente (Alpha Vantage históricos). Contrato público INTOCABLE — mismo cálculo compartido en … _(línea 4490)_
- `quotes_live()` — Lote de cotizaciones en vivo. Body: {"tickers": ["NVDA","TSM","7203.T",…]} (máx 150 por petición; el cliente recorre TODO el catálogo en … _(línea 4506)_
- `macro_fred()` — Fetch FRED series (free, no key). ?series=DXY,T10Y2Y,FEDFUNDS Returns last 30 data points per series. _(línea 4538)_
- `investors_13f(ticker)` — Top institutional holders from SEC EDGAR 13F filings. Cached 24h. _(línea 4573)_
- `trade_flows()` — UN Comtrade public preview API — bilateral semiconductor trade. ?reporter=USA&partner=CHN&product=8542 (optional filters) HS codes: 8541 … _(línea 4626)_
- `trade_history()` _(línea 4698)_
- `portfolio_comment()` — Comentario CAUTO de Khipu sobre el portafolio (papel). Recibe un resumen AGREGADO y anónimo desde el cliente (sin datos personales: solo … _(línea 4711)_
- `portfolio_advice()` — CAPA PROACTIVA (elección de Fabrizio: 'sugiere y tú decides'). Dado un resumen ANÓNIMO de la cartera (papel) + candidatos del universo, … _(línea 4795)_
- `trade_positions_detail()` _(línea 4874)_

**Internas** (empiezan con `_`): `_response_status`, `_degraded`, `_cacheable_response`, `_neg_cache_key`, `_with_negative_cache`, `_cache_cached_ok_only`, `_ai_route_now`, `_ai_models_now`, `_clean_env`, `_norm_alpaca_base`, `_add_security_headers`, `_add_cors_for_public_api`, `_add_graph_version_header`, `_log_request`, `_redact_secrets_in_json`, `_secret_values_for_scan`, `_sw_version`, `_versioned_app_html`, `_js_cache_headers`, `_json_error`, `_research_brief`, `_diag_redact`, `_diag_card`, `_diag_model_name`, `_diag_ai_route`, `_diag_claude`, `_ai_error_fix`, `_ai_error_hint`, `_diag_gemini`, `_diag_nvidia`, `_diag_elevenlabs`, `_db_error_fix`, `_db_error_hint`, `_diag_ontologia`, `_diag_gobernanza`, `_diag_g3_bullets`, `_diag_hot_views`, `_diag_grafo`, `_diag_alpaca`, `_diag_finnhub`, `_diag_fmp`, `_diag_yahoo`, `_diag_research_fix`, `_security_warnings`, `_diag_view`, `_same_origin_request`, `_ws_forbidden`, `_ws_sig`, `_quote_raw_compat`, `_alpaca_hdrs`, `_trade_symbol`, `_paper`, `_account_is_live`, `_house_trading_enabled`, `_house_ledger_block`, `_trading_halted_response`, `_broker_missing_response`, `_trade_actor`, `_trade_audit`, `_alpaca_json` y 23 más

## Depende de

- [[brokerage.api.py]] — importa `(dinámico: brokerage.api)`
- [[brokerage.risk.py]] — importa `trading_enabled`
- [[brokerage.service.py]] — importa `audit`, `poll_fills_job`, `service`
- [[core.__init__.py]] — importa `builder`, `core.gates`, `genui`, `hot_bp`, `known`, `registry`, `report`, `signals`
- [[core.agents_api.py]] — importa `agents_bp`
- [[core.ai.py]] — importa `_ai_complete`, `_ai_configured`, `_ai_json`, `_complete_gemini`, `_complete_nvidia`, `_extract_json`, `ai`, `ai_circuit_state` …
- [[core.ai_usage.py]] — importa `ai_usage`
- [[core.canvas_spec.py]] — importa `hints_prompt`, `sanitize_hints`, `validate_spec`
- [[core.celestrak.py]] — importa `celestrak`
- [[core.company_data.py]] — importa `get_annual_financials`, `get_live_profile`, `get_valuation_news`, `to_dossier`, `to_findossier`
- [[core.config.py]] — importa `AI_MODEL_DEEP`, `AI_MODEL_FAST`, `AI_ORDER`, `CLAUDE`, `FINNHUB`, `GEMINI_KEY`, `GEMINI_MODEL`, `HTTP_TIMEOUT` …
- [[core.decide_api.py]] — importa `(dinámico: core.decide_api)`
- [[core.decision_sites.py]] — importa `decision_sites`
- [[core.decisions.py]] — importa `LedgerUnavailable`
- [[core.geosit.py]] — importa `geo_bp`
- [[core.governance.py]] — importa `governance`
- [[core.governance_api.py]] — importa `(dinámico: core.governance_api)`
- [[core.http.py]] — importa `_rate_buckets`, `_rate_limit`, `_safe_get`, `_safe_ticker`, `rate_limit`, `redact_secrets`, `secret_values`
- [[core.identity.py]] — importa `identity`
- [[core.khipu_chat.py]] — importa `(dinámico: core.khipu_chat)`
- [[core.ledger.py]] — importa `ledger`, `money_gate`
- [[core.ledger_api.py]] — importa `(dinámico: core.ledger_api)`
- [[core.ledger_ddl.py]] — importa `ledger_ddl`
- [[core.ledger_guard.py]] — importa `ledger_guard`
- [[core.live_caps.py]] — importa `_daily_outcomes`, `get_caps`
- [[core.live_fundamentals.py]] — importa `get_all`, `live_fundamentals`
- [[core.logjson.py]] — importa `configure`
- [[core.ops_check.py]] — importa `FIRST_AFTER_BOOT_S`, `ops_bp`, `scheduled`
- [[core.options.py]] — importa `chain_meta`, `vega_report`
- [[core.pin.py]] — importa `client_ip`, `insecure_production_secret`, `pin`, `require_operator`, `require_pin`, `secret_key_default`
- [[core.portfolio_ai.py]] — importa `(dinámico: core.portfolio_ai)`
- [[core.portfolio_reports_api.py]] — importa `(dinámico: core.portfolio_reports_api)`
- [[core.prices_api.py]] — importa `(dinámico: core.prices_api)`
- [[core.prices_store.py]] — importa `prices_store`
- [[core.providers.coingecko.py]] — importa `coingecko`
- [[core.providers.market.py]] — importa `crypto_registry`, `market_registry`
- [[core.providers.news.py]] — importa `news_registry`
- [[core.quotes.py]] — importa `LIVE_MAX_TICKERS`, `_fetch_quote_raw`, `_fx_to_usd`, `fetch_market_cap_yahoo`, `fetch_quotes_live`, `finnhub_circuit_state`, `finnhub_quota_active`
- [[core.replay.py]] — importa `replay`
- [[core.retention.py]] — importa `retention`
- [[core.risk_report.py]] — importa `build_report`
- [[core.scheduler.py]] — importa `scheduler`
- [[core.screener.py]] — importa `screen_growth`
- [[core.semantic.py]] — importa `build_context`, `extract_companies`, `resolve_ids`
- [[core.sim_agents.py]] — importa `sim_agents`
- [[core.space.py]] — importa `(dinámico: core.space)`
- [[core.trading_agent.py]] — importa `_AGENT`, `_AGENT_RESTORE`, `_AgentOrderError`, `_TRADABLE_CACHE`, `_agent_order`, `_agent_run_cycle`, `_agent_universe`, `trading_agent`
- [[core.voice_agent.py]] — importa `voice_agent`
- [[core.voice_api.py]] — importa `BIXBY_SYSTEM_PROMPT`, `RETIRED_VOICE_TOOLS`, `VOICE_COMPANY_VIEWS`, `VOICE_SCREENS`, `VOICE_SCREEN_ALIASES`, `VOICE_SIM_PRESETS`, `VOICE_TOUR_ACTIONS`, `VOICE_UI_ACTIONS` …
- [[core.world.py]] — importa `(dinámico: core.world)`, `world`
- [[matrix.api.py]] — importa `matrix_bp`
- [[matrix.engine.py]] — importa `active_factors`, `build_matrices`, `fragility`, `propagate`
- [[matrix.tensor_api.py]] — importa `tensor_bp`
- [[mcp_server.api.py]] — importa `(dinámico: mcp_server.api)`
- [[ontology.api.py]] — importa `ontology_bp`
- [[ontology.checkpoints.py]] — importa `checkpoints`
- [[ontology.db.py]] — importa `_get_engine`, `init_schema`, `ontology_available`, `schema_outdated`, `session_scope`
- [[ontology.models.py]] — importa `Event`, `LinkRecord`, `ObjectRecord`
- [[ontology.vocabulary.py]] — importa `snapshot`, `unknown_report`
- [[research.api.py]] — importa `research_bp`
- [[research.committee_api.py]] — importa `(dinámico: research.committee_api)`
- [[research.errors.py]] — importa `friendly`
- [[research.health.py]] — importa `health_brief`, `research_health`
- [[research.runner.py]] — importa `recover_orphans_job`, `resume_deferred_job`
- [[scripts.migrate_v0_to_ontology.py]] — importa `run_migration`
- [[app.html]] — lo nombra por su ruta
- [[sw.js]] — lo nombra por su ruta

## Lo usan

- [[core.khipu_chat.py]] — lo importa
- [[security_audit.py]] — lo importa
- [[security_audit.py]] — lo nombra por su ruta

_Además lo importan 67 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/` | `index` | — |
| `POST` | `/api/ai/analyze` | `ai_analyze` | [[core.ai_usage.py]], [[engine.app_coordinator.js]], [[engine.app_main.js]], [[engine.app_preflight.js]], [[engine.brief.js]], [[engine.temporal-graph.js]], 1 prueba |
| `GET` | `/api/ai/debug` | `ai_debug` | 1 prueba |
| `GET` | `/api/ai/usage` | `ai_usage_report` | [[engine.aispend.js]], 1 prueba |
| `POST` | `/api/ai/usage/limits` | `ai_usage_limits` | [[engine.aispend.js]], 2 pruebas |
| `GET` | `/api/candles/<ticker>` | `candles` | [[engine.app_coordinator.js]], [[engine.app_main.js]], [[engine.app_trade_panel.js]], [[engine.fincard.js]], [[engine.localcharts.js]], [[engine.secondbrain.js]] |
| `POST` | `/api/canvas/generate` | `canvas_generate` | [[engine.app_canvas.js]], [[engine.cockpit.js]], [[engine.command_center.js]], 1 prueba |
| `GET` | `/api/company/live/<ticker>` | `company_live` | [[engine.app_main.js]], [[engine.fincard.js]], [[sim.scenario_builder.js]], 1 prueba |
| `GET` | `/api/company/research/<ticker>` | `company_research` | [[engine.app_coordinator.js]] |
| `GET` | `/api/company/valuation/<path:name>` | `company_valuation_news` | [[engine.fincard.js]] |
| `GET` | `/api/crypto/<coin_id>` | `crypto_detail` | [[engine.crypto.js]], [[engine.localcharts.js]], 1 prueba |
| `GET` | `/api/crypto/<coin_id>/history` | `crypto_history` | [[engine.crypto.js]], [[engine.localcharts.js]] |
| `POST` | `/api/crypto/analyze` | `crypto_analyze` | [[engine.crypto.js]], [[engine.localcharts.js]] |
| `GET` | `/api/crypto/markets` | `crypto_markets` | [[engine.crypto.js]], [[engine.localcharts.js]], 1 prueba |
| `POST` | `/api/deep/analyze` | `deep_analyze` | [[engine.cockpit.js]], 1 prueba |
| `GET` | `/api/deep/status` | `deep_status` | [[engine.cockpit.js]], 1 prueba |
| `POST` | `/api/diag` | `client_diag` | [[engine.app_coordinator.js]] |
| `GET` | `/api/diag/recent` | `client_diag_recent` | 1 prueba |
| `GET` | `/api/diagnostics` | `diagnostics` | [[core.ai_usage.py]], [[engine.app_main.js]], 2 pruebas |
| `GET` | `/api/dossier/<ticker>` | `dossier` | [[engine.app_coordinator.js]], 1 prueba |
| `GET` | `/api/earnings/<ticker>` | `earnings` | [[engine.app_main.js]] |
| `GET` | `/api/findossier/<ticker>` | `fin_dossier` | [[engine.cockpit.js]], [[engine.fincard.js]], [[engine.localcharts.js]], [[engine.termdata.js]], 2 pruebas |
| `GET` | `/api/fundamentals/<ticker>` | `fundamentals` | [[engine.app_coordinator.js]], [[engine.app_main.js]], [[engine.khipu_lang.js]], [[engine.termdata.js]], 1 prueba |
| `GET` | `/api/grafo/estado` | `grafo_estado` | [[engine.temporal-graph.js]], 1 prueba |
| `GET` | `/api/health` | `health` | [[app.html]], [[core.ai_usage.py]], [[engine.app_main.js]], 5 pruebas |
| `GET` | `/api/insiders/<ticker>` | `insiders` | [[engine.app_main.js]] |
| `GET` | `/api/investors/13f/<ticker>` | `investors_13f` | [[engine.app_coordinator.js]] |
| `GET` | `/api/ipo_calendar` | `ipo_calendar` | [[engine.app_main.js]] |
| `GET` | `/api/macro/fred` | `macro_fred` | [[engine.app_coordinator.js]] |
| `GET` | `/api/market/live_caps` | `market_live_caps` | [[engine.app_main.js]], 1 prueba |
| `GET` | `/api/market/live_fundamentals` | `market_live_fundamentals` | [[engine.app_main.js]] |
| `GET` | `/api/market/providers` | `market_providers` | 2 pruebas |
| `GET` | `/api/market/quote/<path:symbol>` | `market_quote` | 1 prueba |
| `GET` | `/api/marketstack` | `marketstack_proxy` | [[engine.app_main.js]] |
| `GET` | `/api/news/<ticker>` | `company_news` | [[engine.app_coordinator.js]], [[engine.app_main.js]], [[engine.fincard.js]], [[engine.pfreports.js]], [[engine.temporal-graph.js]], 1 prueba |
| `GET` | `/api/news/gdelt/<company_name>` | `news_gdelt` | [[engine.app_coordinator.js]], [[engine.app_main.js]], [[engine.fincard.js]], [[engine.temporal-graph.js]], [[sim.scenario_builder.js]], 1 prueba |
| `GET` | `/api/options/chain/<symbol>` | `options_chain` | [[engine.riskreport.js]], 1 prueba |
| `POST` | `/api/portfolio-risk` | `api_portfolio_risk_internal` | [[engine.app_coordinator.js]] |
| `POST` | `/api/portfolio/advice` | `portfolio_advice` | [[engine.cockpit.js]] |
| `POST` | `/api/portfolio/comment` | `portfolio_comment` | [[engine.cockpit.js]], 1 prueba |
| `POST` | `/api/portfolio/risk_report` | `portfolio_risk_report` | [[engine.riskreport.js]], 2 pruebas |
| `POST` | `/api/portfolio/vega_report` | `portfolio_vega_report` | [[engine.riskreport.js]], 1 prueba |
| `GET` | `/api/quote/<ticker>` | `quote` | [[engine.app_main.js]], 2 pruebas |
| `GET` | `/api/quotes` | `batch_quotes` | [[engine.canvas-data.js]], 2 pruebas |
| `POST` | `/api/quotes/live` | `quotes_live` | [[engine.app_main.js]], [[engine.worldmonitor.js]], 1 prueba |
| `GET` | `/api/scalp/price/<path:symbol>` | `scalp_price` | [[engine.cockpit.js]], 2 pruebas |
| `GET` | `/api/screener/growth` | `screener_growth` | [[engine.cockpit.js]], 2 pruebas |
| `POST` | `/api/sim/agents` | `sim_agents_route` | [[core.ai_usage.py]], [[core.decision_sites.py]], [[engine.app_coordinator.js]], [[engine.cockpit.js]], 2 pruebas |
| `GET` | `/api/space/launches` | `space_launches` | [[engine.voice.js]], 1 prueba |
| `GET` | `/api/space/tle` | `space_tle` | [[engine.spacemonitor.js]], [[engine.voice.js]], 1 prueba |
| `GET` | `/api/supply-chain/trade-flows` | `trade_flows` | [[engine.app_coordinator.js]] |
| `POST` | `/api/thesis/quick` | `thesis_quick` | [[core.ai_usage.py]], [[engine.cockpit.js]], 2 pruebas |
| `GET` | `/api/trade/account` | `trade_account` | [[engine.app_trade_panel.js]], [[engine.trade.js]], 1 prueba |
| `POST` | `/api/trade/close` | `trade_close` | [[engine.cockpit.js]], 2 pruebas |
| `GET` | `/api/trade/crypto/assets` | `trade_crypto_assets` | [[engine.crypto.js]], [[engine.trade.js]] |
| `GET` | `/api/trade/diag` | `trade_diag` | — |
| `GET` | `/api/trade/history` | `trade_history` | [[engine.app_trade_panel.js]], [[engine.cockpit.js]], [[engine.toast.js]], 2 pruebas |
| `POST` | `/api/trade/order` | `trade_order` | [[engine.app_trade_panel.js]], [[engine.crypto.js]], [[engine.trade.js]], 2 pruebas |
| `GET` | `/api/trade/positions/detail` | `trade_positions_detail` | [[engine.app_trade_panel.js]], [[engine.cockpit.js]], [[engine.pfcommittee.js]], [[engine.voice.js]], 2 pruebas |
| `GET` | `/api/trade/status` | `trade_status` | [[app.html]], 1 prueba |
| `GET` | `/api/vocabulary` | `api_vocabulary` | 2 pruebas |
| `GET` | `/api/vocabulary/unknown` | `api_vocabulary_unknown` | — |
| `POST` | `/api/ws-key` | `ws_key` | [[engine.app_main.js]], 1 prueba |
| `GET` | `/api/ws-token` | `ws_token` | [[engine.app_main.js]], 1 prueba |
| `GET` | `/docs` | `api_docs` | — |
| `GET` | `/engine/<path:filename>` | `serve_engine` | — |
| `GET` | `/icon.svg` | `icon` | — |
| `GET` | `/manifest.webmanifest` | `manifest` | — |
| `GET` | `/nodes/<path:filename>` | `serve_nodes` | — |
| `GET` | `/sim/<path:filename>` | `serve_sim` | — |
| `GET` | `/sw.js` | `service_worker` | — |
| `POST` | `/v1/auth/key` | `api_issue_key` | [[engine.app_main.js]], [[security_audit.py]] |
| `GET` | `/v1/nodes` | `api_nodes` | — |
| `GET` | `/v1/nodes/<node_id>/live` | `api_node_live` | — |
| `POST` | `/v1/risk/portfolio` | `api_portfolio_risk` | 1 prueba |
| `GET` | `/vendor/<path:name>` | `vendor` | — |

Grupos: [[API ai]], [[API candles]], [[API canvas]], [[API company]], [[API crypto]], [[API deep]], [[API diag]], [[API diagnostics]], [[API dossier]], [[API earnings]], [[API findossier]], [[API fundamentals]], [[API grafo]], [[API health]], [[API insiders]], [[API investors]], [[API ipo_calendar]], [[API macro]], [[API market]], [[API marketstack]], [[API news]], [[API options]], [[API portfolio]], [[API portfolio-risk]], [[API páginas y archivos estáticos]], [[API quote]], [[API quotes]], [[API scalp]], [[API screener]], [[API sim]], [[API space]], [[API supply-chain]], [[API thesis]], [[API trade]], [[API v1 (pública)]], [[API vocabulary]], [[API ws-key]], [[API ws-token]]

## Endpoints que llama

- `DELETE /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `GET /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `OPTIONS /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])
- `POST /api/ws-key` → [[server.py]] ([[API ws-key]])
- `POST /mcp` → [[mcp_server.api.py]] ([[API MCP transporte y OAuth]])

## Variables de entorno que lee (solo nombres)

- [[ENV ALPACA_BASE]]
- [[ENV ALPACA_KEY]]
- [[ENV ALPACA_SECRET]]
- [[ENV ALPHA_VANTAGE_KEY]]
- [[ENV AV_KEY]]
- [[ENV BROKERAGE_TRADING_ENABLED]]
- [[ENV CSP_ENABLED]]
- [[ENV CSP_REPORT_ONLY]]
- [[ENV ELEVENLABS_AGENT_ID]]
- [[ENV ELEVENLABS_KEY]]
- [[ENV FINNHUB_WS_KEY]]
- [[ENV FMP_KEY]]
- [[ENV KHIPU_ADMIN_SECRET]]
- [[ENV MARKETSTACK_KEY]]
- [[ENV PORT]]
- [[ENV REDIS_URL]]
- [[ENV REMIGRATE_ON_BOOT]]
- [[ENV SECRET_KEY]]
- [[ENV SEC_USER_AGENT]]
- [[ENV TRADE_PIN]]

## Pruebas que lo cubren

- [[tests.test_ai_json.py]]
- [[tests.test_ai_usage.py]]
- [[tests.test_bitemporal.py]]
- [[tests.test_canvas.py]]
- [[tests.test_chat_portfolio_agent.py]]
- [[tests.test_checkpoints.py]]
- [[tests.test_cierre_infra.py]]
- [[tests.test_cleanup_client.py]]
- [[tests.test_cleanup_modules_theme_i18n.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_client_hardening.py]]
- [[tests.test_company_data.py]]
- [[tests.test_csp_estricta.py]]
- [[tests.test_gates_resulting_state.py]]
- [[tests.test_genui_browser.py]]
- [[tests.test_governance.py]]
- [[tests.test_governance_activation.py]]
- [[tests.test_governance_flow.py]]
- [[tests.test_graph_api.py]]
- [[tests.test_hot_contract.py]]
- [[tests.test_hot_invalidation.py]]
- [[tests.test_hot_review_fixes.py]]
- [[tests.test_hot_views_parity.py]]
- [[tests.test_infra.py]]
- [[tests.test_ingest_news.py]]
- [[tests.test_jev_status_label.py]]
- [[tests.test_kernel_reference_figures.py]]
- [[tests.test_khipus_os_server.py]]
- [[tests.test_ledger_anchor.py]]
- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_live_caps.py]]
- [[tests.test_matrix.py]]
- [[tests.test_neo4j_retirado.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_ontology_agents.py]]
- [[tests.test_ontology_alerts.py]]
- [[tests.test_ops_events_append_only.py]]
- [[tests.test_ops_single_source.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_overnight2_fixer_review.py]]
- [[tests.test_overnight2_scenes_tokens.py]]
- [[tests.test_overnight3_diag_bilingual.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_overnight_voice_server.py]]
- [[tests.test_phase3.py]]
- [[tests.test_portfolio_ai.py]]
- [[tests.test_portfolio_persist.py]]
- [[tests.test_portfolio_reports.py]]
- [[tests.test_prices_eod.py]]
- [[tests.test_provenance.py]]
- [[tests.test_providers.py]]
- [[tests.test_quotes_live.py]]
- [[tests.test_reconcile.py]]
- [[tests.test_repair_committee.py]]
- [[tests.test_repair_ontology_review.py]]
- [[tests.test_repair_ops.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_research.py]]
- [[tests.test_review_batch_g.py]]
- [[tests.test_review_infra_c.py]]
- [[tests.test_risk_easy.py]]
- [[tests.test_risk_options.py]]
- [[tests.test_rutas_acceso_decision.py]]
- [[tests.test_scenario_pnl.py]]
- [[tests.test_scenario_pnl_browser.py]]
- [[tests.test_security.py]]
- [[tests.test_server_smoke.py]]
- [[tests.test_space_satellites.py]]
- [[tests.test_trading_agent_ledger.py]]
- [[tests.test_voice_agent_split.py]]
- [[tests.test_voice_os_server.py]]
- [[tests.test_voice_tour.py]]
- [[tests.test_voice_tour_client.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (k) — FASE 2+ LOTE I - rutas con decisión, CSP estricta, riesgo]]
- [[Sesión 2026-10-13 (i) — NEO4J RETIRADO (decisión 6 de Fabrizio) — sw v264]]
- [[Sesión 2026-10-11 (c) — LA VOZ DE KHIPU PARA KHIPUS OS + RECORRIDO DE UN MINUTO CON SU]]
- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-09-22 al 24 — PHASE 1 Live Investment Graph COMPLETA + velocidad + 3D temporal]]
- [[Sesión 2026-09-21 — Limpieza estructural - Track A Fase 2 + Track B completos]]
- [[Sesión 2026-07-05 — Etapa 1 — Limpieza masiva - COMPLETA (4 batches publicados)]]
- [[Sesión 2026-07-07 — Etapa 3 — Motor de matrices + hiperaristas - NÚCLEO COMPLETO]]
- [[Sesión 2026-07 — Ampliaciones (tras feedback simulaciones muy cerradas, más info)]]
- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
- [[Sesión 2026-07-13 — Etapa M — Trading cripto en papel, integrado en Khipu (sw v80)]]
- [[Sesión 2026-07-13 — Etapa O — Khipus Finance AI - 9 frentes + rebrand + Cabina inicial]]
