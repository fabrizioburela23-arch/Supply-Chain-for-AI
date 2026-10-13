---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/app_main.js"
lenguaje: "javascript"
lineas: 4805
aliases: ["engine/app_main.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/app_main.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 4.805 líneas · `engine/app_main.js`

## Para qué sirve

Global error reporter — shows uncaught JS errors on screen (no devtools needed)

## API pública (globales que define)

`window.APP_NAME`, `window.ASSISTANT_NAME`, `window.CATS`, `window.CAT_TO_SECTOR`, `window.DataLayer`, `window.KhipuLive`, `window.KhipuLiveCaps`, `window.KhipuLiveFund`, `window.LANG`, `window.LINKS`, `window.NODES`, `window.NODE_BY_ID`, `window.NODE_META`, `window.NRS_FLOW_TYPES`, `window.OntologyAlerts`, `window.SECTORS9`, `window.V8detail`, `window.V8feed`, `window.__khOsGaveUp`, `window._appVersion`, `window._buildNrsDegree`, `window._canonId`, `window._ensureMapSettled`, `window._injectGraphContext`, `window._invalidateNRS`, `window._khipuLoaderDismiss`, `window._khipuLoaderFallback`, `window._lblOn`, `window._liveLoading`, `window._liveRecolorByImpact`, `window._liveResetColors`, `window._liveSelectedNode`, `window._liveTintLinks`, `window._mapLayers`, `window._mapState`, `window._resizeNodesByCap`, `window._selectedNode`, `window._showUpdatePill`, `window._tickerWarnings`, `window._toggleColorMode`, `window._updPending`, `window.addToPortfolio`, `window.applyVerifiedValuations`, `window.clearStressBtn`, `window.closePropuestas`, `window.closeSistema`, `window.computeNRS`, `window.computeNRSBreakdown`, `window.esc`, `window.fillLiveMcap`, `window.fillLiveMeta`, `window.goMap`, `window.jumpTo`, `window.lanzarInvestigacion`, `window.liveCapDot`, `window.loadLiveQuotes`, `window.loadStockChart`, `window.openDiagnostics`, `window.openPropuestas`, `window.openRegistro`, `window.openSistema`, `window.posCancel`, `window.posDel`, `window.posEdit`, `window.posSave`, `window.quoteAge`, `window.quoteAgoText`, `window.quoteExchange`, `window.quoteIsLive`, `window.quotePx`, `window.quoteSrcChip`, `window.quoteSrcName`, `window.refreshStyles`, `window.runAgentes`, `window.sectorName`, `window.setChartMode`, `window.settleGraph`, `window.stressBtn`

De nivel superior (globales del script): `BASE`, `GEO_REGIONS`, `GEO_REGION_OF`, `I18N`, `LBL_MAX`, `LINK_TYPE_COLORS`, `LIVE_BATCH`, `LT_ORDER`, `MAP_FIRST_ALPHA`, `MAP_POS_KEY`, `MKT`, `SERVER_MODE`, `STRESS_DEAD_PCT`, `USER_PORTFOLIOS`, `V8`, `W`, `_NRS_GEO`, `_NRS_GEO_ALIAS`, `_afterQuotesMerged`, `_alphaDecay`, `_bcCache`, `_capResizeT`, `_chargeStr`, `_chartModes`, `_deselect`, `_filterCache`, `_lblMinR`, `_ldrSet`, `_liveTick`, `_loaderBar`, `_loaderText`, `_mapBootWaiting`, `_mapCkOpen`, `_mapCkSeen`, `_mapClassicBoot`, `_mapCovered`, `_mapFirstRecipe`, `_mapFirstSettleAsync`, `_mapFitPending`, `_mapFlyPending`, `_mapHint`, `_mapHintEl`, `_mapLaidNow`, `_mapLaidOnce`, `_mapOsExpected`, `_mapPosSave`, `_mapPosSaveSoon`, `_mapPosSaveT`, `_mapPosSeed`, `_mapPost`, `_mapReheat`, `_mapSeeded`, `_mapSettleJob`, `_mapSig`, `_mergeLiveQuote`, `_mergeResult`, `_mixHex`, `_nodeCount`, `_nrsCache`, `_nrsCountry`, `_nrsDegree`, `_nrsTerms`, `_paintGraph`, `_persistQuotes`, `_processMktData`, `_recalcLblMin`, `_refreshStylesCore`, `_resizeT`, `_resolveId`, `_selectNode`, `_showEventsAlert`, `_stockCache`, `activateStress`, `activeTab`, `applyLang`, `applyView`, `backdropEl`, `bandEl`, `bfsPath`, `buildFilterCache` y 99 más

## Depende de

- [[app.html]] — usa `_tradeErrText`, `_tradeFetch`, `khJSON`, `safeUrl`
- [[engine.aispend.js]] — usa `KhipuSpend`
- [[engine.app_canvas.js]] — usa `initCanvasTab`
- [[engine.app_coordinator.js]] — usa `_dossierRedrawIfNeeded`, `_dossierRelabel`, `_termRefreshPrices`, `initGdelt`, `initSimTab`, `initSpaceTab`, `initTerminalTab`, `renderNrsTop10`
- [[engine.app_trade_panel.js]] — usa `openTradeModal`
- [[engine.audit.js]] — usa `KhipuAudit`
- [[engine.cockpit.js]] — usa `BixbyCockpit`
- [[engine.crypto.js]] — usa `KhipuCrypto`
- [[engine.explain.js]] — usa `explainChip`, `explainMetric`
- [[engine.governance.js]] — usa `KhipuGovernance`
- [[engine.graph3d.js]] — usa `_graph3d_updateLiveColors`
- [[engine.guide.js]] — usa `initGuiaTab`
- [[engine.insights.js]] — usa `renderInsightsHistory`, `renderKhipuInsights`
- [[engine.maptime.js]] — usa `KhipuMapTime`, `_mapTimePaint`
- [[engine.matrixview.js]] — usa `renderMatrixView`
- [[engine.mcpconnect.js]] — usa `KhipuMCP`
- [[engine.portfolios.js]] — usa `KhipuPortfolios`
- [[engine.pricehist.js]] — usa `KhipuPriceHistory`
- [[engine.reconcile.js]] — usa `KhipuReconcile`
- [[engine.research.js]] — usa `KhipuResearch`
- [[engine.temporal-graph.js]] — usa `initTKGTab`
- [[engine.toast.js]] — usa `khipuActor`
- [[engine.worldmonitor.js]] — usa `KhipuWorld`
- [[engine.xray.js]] — usa `openXRay`
- [[nodes.links_all.js]] — usa `LINKS_SPACEX`
- [[nodes.links_connect.js]] — usa `LINKS_CONNECT`
- [[nodes.links_expand.js]] — usa `LINKS_EXPAND`
- [[nodes.listing_status.js]] — usa `LISTING_STATUS`
- [[nodes.merge_graph.js]] — usa `buildKhipusGraph`
- [[nodes.nodes_china.js]] — usa `LINKS_CHINA`, `NODES_CHINA`
- [[nodes.nodes_expand.js]] — usa `NODES_EXPAND`
- [[nodes.nodes_expand2.js]] — usa `NODES_EXPAND2`
- [[nodes.nodes_expand3.js]] — usa `NODES_EXPAND3`
- [[nodes.nodes_expand4.js]] — usa `LINKS_EXPAND4`, `NODES_EXPAND4`
- [[nodes.nodes_expand5.js]] — usa `LINKS_EXPAND5`, `NODES_EXPAND5`
- [[nodes.nodes_multicapa.js]] — usa `LINKS_MULTICAPA`, `NODES_MULTICAPA`
- [[nodes.nodes_nuclear.js]] — usa `LINKS_NUCLEAR`, `NODES_NUCLEAR`
- [[nodes.nodes_seed.js]] — usa `CATS`, `CATS_NEW`, `CAT_TO_SECTOR`, `COUNTRIES`, `INVEST_PATH`, `LOGO_DOMAIN`, `NODES`, `NODE_ID_ALIAS`, `NODE_META`, `RAW_LINKS` y 2 más
- [[nodes.nodes_spacex.js]] — usa `NODES_SPACEX`
- [[nodes.preipo_intel.js]] — usa `PREIPO_INTEL`
- [[nodes.private_valuations.js]] — usa `PRIVATE_VALUATIONS`
- [[sw.js]] — lo nombra por su ruta

Se carga en [[app.html]] en la posición **24 de 97** (línea 2611), después de [[nodes.merge_graph.js]] y antes de [[engine.loading.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 24)
- [[app.html]] — usa `BASE`, `LANG`, `_injectGraphContext`, `_showUpdatePill`, `closeSistema`, `lanzarInvestigacion`, `loadCorporateEvents`, `openDiagnostics` y 5 más
- [[engine.aispend.js]] — usa `BASE`, `LANG`
- [[engine.app_canvas.js]] — usa `LANG`, `MKT`, `_selectedNode`, `computeNRS`
- [[engine.app_coordinator.js]] — usa `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `_appVersion`, `_liveLoading`, `activeTab`, `applyLang` y 16 más
- [[engine.app_preflight.js]] — usa `LINKS`, `MKT`, `NODE_BY_ID`, `computeNRS`, `jumpTo`, `switchTab`
- [[engine.app_scatter.js]] — usa `LANG`
- [[engine.app_trade_panel.js]] — usa `LANG`, `MKT`, `activeTab`, `applyLang`, `esc`, `quotePx`, `renderMarket`, `savePos`
- [[engine.audit.js]] — usa `BASE`, `LANG`
- [[engine.brief.js]] — usa `LANG`, `MKT`, `NODE_BY_ID`, `computeNRS`, `jumpTo`, `switchTab`
- [[engine.canvas-data.js]] — usa `BASE`
- [[engine.clients.js]] — usa `LANG`
- [[engine.cockpit.js]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `_ensureMapSettled`, `_liveRecolorByImpact`, `_liveSelectedNode`, `catLabel` y 8 más
- [[engine.command_center.js]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `activateStress`, `computeNRS`, `jumpTo`, `switchTab`
- [[engine.committee.js]] — usa `BASE`, `LANG`, `NODE_BY_ID`
- [[engine.compare.js]] — usa `LANG`, `LINKS`, `NODE_BY_ID`, `computeNRS`, `computeNRSBreakdown`, `sectorName`
- [[engine.crypto.js]] — usa `LANG`, `t`
- [[engine.desktop.js]] — usa `LANG`
- [[engine.explain.js]] — usa `LANG`
- [[engine.fincard.js]] — usa `BASE`, `LANG`, `NODE_BY_ID`
- [[engine.globe.js]] — usa `BASE`, `LINKS`, `computeNRS`
- [[engine.governance.js]] — usa `BASE`, `LANG`
- [[engine.graph3d.js]] — usa `LINKS`, `NODE_BY_ID`, `_tickerWarnings`, `computeNRS`, `computeNodeRadius`, `getCatColorHex`, `getLinkColorHex`, `jumpTo` y 2 más
- [[engine.guide.js]] — usa `LANG`, `LINKS`, `NODE_BY_ID`
- [[engine.hypergraph.js]] — usa `DataLayer`, `NODE_BY_ID`, `getCatColorHex`
- [[engine.insights.js]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `activateStress`, `computeNRS`, `jumpTo`, `sectorName` y 1 más
- [[engine.khipu_chat.js]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `_liveSelectedNode`, `_selectedNode`, `activeTab`, `jumpTo` y 1 más
- [[engine.khipu_lang.js]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `switchTab`
- [[engine.layers.js]] — usa `LANG`
- [[engine.live.js]] — usa `BASE`, `LANG`, `MKT`, `_appVersion`, `_showUpdatePill`
- [[engine.livesim.js]] — usa `LANG`, `MKT`, `NODE_BY_ID`, `_liveRecolorByImpact`, `_liveResetColors`, `_liveSelectedNode`, `_liveTintLinks`, `jumpTo` y 1 más
- [[engine.localcharts.js]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `_selectedNode`, `computeNRS`, `computeNRSBreakdown` y 2 más
- [[engine.maptime.js]] — usa `BASE`, `LANG`, `LINKS`, `NODE_BY_ID`, `_mapLayers`, `computeNodeRadius`, `getLinkColorHex`, `jumpTo` y 3 más
- [[engine.mascot.js]] — usa `LANG`
- [[engine.matrixview.js]] — usa `LANG`, `LINKS`, `NODE_BY_ID`, `sectorName`
- [[engine.mcpconnect.js]] — usa `LANG`, `closeSistema`
- [[engine.nav4.js]] — usa `activeTab`, `switchTab`
- [[engine.orb.js]] — usa `LANG`
- [[engine.oswindows.js]] — usa `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `_canonId`, `loadLiveQuotes`, `quoteAge`, `quoteAgoText` y 3 más
- [[engine.pfcommittee.js]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`
- [[engine.pfreports.js]] — usa `BASE`, `LANG`
- [[engine.pickers.js]] — usa `LANG`, `NODE_BY_ID`
- [[engine.portfolios.js]] — usa `LANG`, `MKT`, `NODE_BY_ID`, `fetchQuotes`
- [[engine.pricehist.js]] — usa `BASE`, `LANG`
- [[engine.reconcile.js]] — usa `BASE`, `LANG`
- [[engine.research.js]] — usa `BASE`, `LANG`, `NODE_BY_ID`, `jumpTo`
- [[engine.resolve.js]] — usa `LANG`, `NODE_BY_ID`, `activateStress`, `closeSistema`, `jumpTo`, `loadStockChart`, `switchTab`
- [[engine.riskreport.js]] — usa `BASE`, `DataLayer`, `LANG`, `MKT`, `NODE_BY_ID`
- [[engine.secondbrain.js]] — usa `DataLayer`, `LANG`, `LINKS`, `NODE_BY_ID`, `NRS_FLOW_TYPES`, `V8detail`, `activateStress`, `catColor` y 9 más
- [[engine.spacemonitor.js]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `computeNRS`, `jumpTo`, `quotePx` y 1 más
- [[engine.statematrix.js]] — usa `MKT`, `NODE_BY_ID`, `computeNRS`, `quotePx`
- [[engine.sync.js]] — usa `BASE`, `MKT`, `renderMarket`
- [[engine.temporal-graph.js]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `SERVER_MODE`, `catLabel`, `computeNRS` y 4 más
- [[engine.termdata.js]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `computeNRS`, `fillLiveMeta`, `liveCapDot` y 1 más
- [[engine.timeline3d.js]] — usa `LANG`, `NODE_BY_ID`, `getLinkColorHex`
- [[engine.toast.js]] — usa `LANG`
- [[engine.trade.js]] — usa `LANG`
- [[engine.universe2d.js]] — usa `LANG`, `computeNRS`, `computeNodeRadius`, `getCatColorHex`, `jumpTo`
- [[engine.voice.js]] — usa `BASE`, `KhipuLive`, `LANG`, `LINKS`, `NODE_BY_ID`, `NRS_FLOW_TYPES`, `V8`, `_canonId` y 10 más
- [[engine.worldmonitor.js]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `computeNRS`, `goMap`, `switchTab`
- [[engine.xray.js]] — usa `DataLayer`, `KhipuLive`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `activateStress`, `computeNRS` y 8 más
- [[sim.scenario_builder.js]] — usa `BASE`, `NODE_BY_ID`, `quotePx`

## Endpoints que llama

- `DELETE /api/ontology/alerts/<alert_id>` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/candles/<ticker>` → [[server.py]] ([[API candles]])
- `GET /api/company/live/<ticker>` → [[server.py]] ([[API company]])
- `GET /api/diagnostics` → [[server.py]] ([[API diagnostics]])
- `GET /api/earnings/<ticker>` → [[server.py]] ([[API earnings]])
- `GET /api/fundamentals/<ticker>` → [[server.py]] ([[API fundamentals]])
- `GET /api/health` → [[server.py]] ([[API health]])
- `GET /api/insiders/<ticker>` → [[server.py]] ([[API insiders]])
- `GET /api/ipo_calendar` → [[server.py]] ([[API ipo_calendar]])
- `GET /api/market/live_caps` → [[server.py]] ([[API market]])
- `GET /api/market/live_fundamentals` → [[server.py]] ([[API market]])
- `GET /api/marketstack` → [[server.py]] ([[API marketstack]])
- `GET /api/news/<ticker>` → [[server.py]] ([[API news]])
- `GET /api/news/gdelt/<company_name>` → [[server.py]] ([[API news]])
- `GET /api/ontology/actions` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/agents/proposals` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/alerts/check` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/feed` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/objects/<object_id>/timeline` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/quote/<ticker>` → [[server.py]] ([[API quote]])
- `GET /api/ws-token` → [[server.py]] ([[API ws-token]])
- `POST /api/ai/analyze` → [[server.py]] ([[API ai]])
- `POST /api/news/portfolio` → [[core.portfolio_reports_api.py]] ([[API news]])
- `POST /api/ontology/agents/investigar` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/agents/proposals/<proposal_id>/approve` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/agents/proposals/<proposal_id>/reject` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/agents/run` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/ingest/news` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/quotes/live` → [[server.py]] ([[API quotes]])
- `POST /api/ws-key` → [[server.py]] ([[API ws-key]])
- `POST /v1/auth/key` → [[server.py]] ([[API v1 (pública)]])

## Pruebas que lo cubren

- [[tests.test_app_split.py]]
- [[tests.test_client_hardening.py]]
- [[tests.test_market_keys_scope.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (m) — app.html PARTIDO + 2 arreglos visibles — sw v268]]
- [[Sesión 2026-10-13 (l) — APP.HTML PARTIDO SIN CAMBIAR NADA (G5-06) — sw v267]]
