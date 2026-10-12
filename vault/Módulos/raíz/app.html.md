---
tipo: "pagina"
capa: "Interfaz (Khipus OS)"
ruta: "app.html"
lenguaje: "html"
lineas: 12665
aliases: ["app.html"]
tags: ["capa/interfaz", "tipo/pagina"]
---

# app.html

> Página · capa [[Capa Interfaz (Khipus OS)]] · 12.665 líneas · `app.html`

## Para qué sirve

Khipus Finance Intelligence · 2026: TODA la interfaz en un solo archivo HTML. Arranca Khipus OS (la Cabina con el chat y las ventanas); la vista clásica conserva las pestañas.

## Pestañas

| Botón | data-tab | Grupo | id |
|---|---|---|---|
| ⬡ Cadena | `map` | `mapa` | `tab-map` |
| 🌐 Geopolítica | `geo` | `mapa` | `tab-geo` |
| 🚀 Espacio | `space` | `mapa` | `tab-space` |
| 🧬 Simulación | `simulation` | `mapa` | `tab-sim` |
| 🪐 Universo | `—` | `mapa` | `tab-3d` |
| 📈 Mercado en Vivo | `market` | `mercado` | `tab-market` |
| ₿ Cripto | `crypto` | `mercado` | `tab-crypto` |
| 💼 Carteras | `portfolios` | `mercado` | `tab-portfolios` |
| 🏛 Comité | `—` | `mercado` | `tab-committee` |
| 👥 Clientes | `—` | `mercado` | `tab-clients` |
| 🔬 Análisis de Red | `analysis` | `insights` | `tab-analysis` |
| ✦ Canvas IA | `canvas` | `insights` | `tab-canvas` |
| ⬛ Terminal | `terminal` | `insights` | `tab-terminal` |
| ❓ Guía | `guia` | `guia` | `tab-guia` |

## Orden de carga de scripts

1. `vendor/d3.min.js` — externo/vendor (línea 10)
2. [[nodes.nodes_seed.js]] (línea 1437)
3. [[nodes.nodes_expand.js]] (línea 1438)
4. [[nodes.nodes_expand2.js]] (línea 1439)
5. [[nodes.nodes_spacex.js]] (línea 1440)
6. [[nodes.nodes_expand3.js]] (línea 1441)
7. [[nodes.nodes_nuclear.js]] (línea 1442)
8. [[nodes.nodes_expand4.js]] (línea 1443)
9. [[nodes.nodes_expand5.js]] (línea 1444)
10. [[nodes.meta_fill.js]] (línea 1445)
11. [[nodes.nodes_china.js]] (línea 1446)
12. [[nodes.nodes_multicapa.js]] (línea 1447)
13. [[nodes.preipo_intel.js]] (línea 1448)
14. [[nodes.listing_status.js]] (línea 1449)
15. [[nodes.private_valuations.js]] (línea 1450)
16. [[nodes.links_all.js]] (línea 1451)
17. [[nodes.links_expand.js]] (línea 1452)
18. [[nodes.links_connect.js]] (línea 1453)
19. [[nodes.merge_graph.js]] (línea 1454)
20. `vendor/three.min.js` — externo/vendor (línea 1455)
21. `vendor/chart.umd.min.js` — externo/vendor (línea 1456)
22. `vendor/satellite.min.js` — externo/vendor (línea 1457)
23. bloque `<script>` inline #1 (línea 1483, 326 líneas)
24. bloque `<script>` inline #2 (línea 2590, 4.817 líneas)
25. bloque `<script>` inline #3 (línea 7691, 119 líneas)
26. [[engine.loading.js]] (línea 7812)
27. [[engine.toast.js]] (línea 7813)
28. [[engine.agents_registry.js]] (línea 7814)
29. [[engine.tour_script.js]] (línea 7815)
30. [[engine.mascot.js]] (línea 7816)
31. [[engine.universe2d.js]] (línea 7817)
32. [[engine.resolve.js]] (línea 7818)
33. [[engine.orb.js]] (línea 7819)
34. [[engine.voice.js]] (línea 7820)
35. [[engine.secondbrain.js]] (línea 7821)
36. [[engine.geo_coords.js]] (línea 7822)
37. [[engine.globe.js]] (línea 7823)
38. [[engine.canvas-data.js]] (línea 7824)
39. [[nodes.temporal_seed_facts.js]] (línea 7825)
40. [[nodes.temporal_seed_facts2.js]] (línea 7826)
41. [[nodes.ontology.js]] (línea 7827)
42. [[nodes.ontology_facts.js]] (línea 7828)
43. [[nodes.legal_names.js]] (línea 7829)
44. [[engine.temporal-graph.js]] (línea 7830)
45. [[engine.timeline3d.js]] (línea 7831)
46. [[engine.maptime.js]] (línea 7832)
47. [[engine.khipu_lang.js]] (línea 7833)
48. [[engine.guide.js]] (línea 7834)
49. [[engine.xray.js]] (línea 7835)
50. [[engine.research.js]] (línea 7836)
51. bloque `<script>` inline #4 (línea 7837, 52 líneas)
52. [[engine.riskreport.js]] (línea 7889)
53. [[engine.worldmonitor.js]] (línea 7890)
54. [[engine.spacemonitor.js]] (línea 7891)
55. [[engine.pickers.js]] (línea 7892)
56. [[engine.committee.js]] (línea 7893)
57. [[engine.aispend.js]] (línea 7894)
58. [[engine.pfcommittee.js]] (línea 7895)
59. [[engine.pfreports.js]] (línea 7896)
60. [[engine.sync.js]] (línea 7897)
61. [[engine.clients.js]] (línea 7898)
62. [[engine.mcpconnect.js]] (línea 7899)
63. bloque `<script>` inline #5 (línea 7900, 16 líneas)
64. [[engine.insights.js]] (línea 7916)
65. [[engine.statematrix.js]] (línea 7917)
66. [[engine.livesim.js]] (línea 7918)
67. [[engine.layers.js]] (línea 7919)
68. [[engine.brief.js]] (línea 7920)
69. [[engine.compare.js]] (línea 7921)
70. [[engine.matrixview.js]] (línea 7922)
71. [[engine.nav4.js]] (línea 7923)
72. [[engine.localcharts.js]] (línea 7924)
73. [[engine.fincard.js]] (línea 7925)
74. [[engine.termdata.js]] (línea 7926)
75. [[engine.explain.js]] (línea 7927)
76. [[engine.reconcile.js]] (línea 7928)
77. [[nodes.crypto_intel.js]] (línea 7929)
78. [[nodes.crypto_intel2.js]] (línea 7930)
79. [[engine.crypto.js]] (línea 7931)
80. [[engine.portfolios.js]] (línea 7932)
81. [[engine.oswindows.js]] (línea 7933)
82. [[engine.khipu_chat.js]] (línea 7934)
83. [[engine.desktop.js]] (línea 7935)
84. [[engine.cockpit.js]] (línea 7936)
85. [[engine.live.js]] (línea 7937)
86. [[engine.command_center.js]] (línea 7938)
87. [[sim.scenario_builder.js]] (línea 7939)
88. bloque `<script>` inline #6 (línea 7941, 2.694 líneas)
89. bloque `<script>` inline #7 (línea 10935, 608 líneas)
90. bloque `<script>` inline #8 (línea 11545, 143 líneas)
91. bloque `<script>` inline #9 (línea 11690, 690 líneas)
92. bloque `<script>` inline #10 (línea 12381, 282 líneas)

## Bloques `<script>` inline

| # | Línea | Líneas | Funciones | Cabecera |
|---|---|---|---|---|
| 1 | 1483 | 326 | 11 | Hard fallback: always dismiss \#boot after 3s even if main JS crashes |
| 2 | 2590 | 4.817 | 147 | Global error reporter — shows uncaught JS errors on screen (no devtools needed) |
| 3 | 7691 | 119 | 4 | Lissajous spirograph — same math renders at any size |
| 4 | 7837 | 52 | 3 | AVISO "SERVIDOR NO DISPONIBLE" (incidente 2026-09-29: Railway dejó de responder y la app mostraba EN SILENCIO la última versión guardada por el service worker … |
| 5 | 7900 | 16 | 1 | Insignia en 👥 Clientes: propuestas (de agentes MCP o del comité) esperando aprobación humana. Nunca pide el PIN (pendingCount devuelve null sin PIN). |
| 6 | 7941 | 2.694 | 73 | Khipu Core Coordinator |
| 7 | 10935 | 608 | 11 | Professional Trade Panel |
| 8 | 11545 | 143 | 4 | Preflight debounce wiring |
| 9 | 11690 | 690 | 37 | palette & helpers |
| 10 | 12381 | 282 | 16 | KHIPU FINANCE — Scatter 3D Semántico con Medidores Botón 📊: posiciona empresas en ejes semánticos + panel de medidores interactivo |

## API pública (globales window.* que define)

`window.APP_NAME`, `window.ASSISTANT_NAME`, `window.BixbyVoice`, `window.CATS`, `window.CAT_TO_SECTOR`, `window.DataLayer`, `window.KhipuLive`, `window.KhipuLiveCaps`, `window.KhipuLiveFund`, `window.LANG`, `window.LINKS`, `window.NODES`, `window.NODE_BY_ID`, `window.NODE_META`, `window.NRS_FLOW_TYPES`, `window.OntologyAlerts`, `window.SECTORS9`, `window.V8detail`, `window.V8feed`, `window.__khOsGaveUp`, `window.__khStaleReloaded`, `window.__tradeAcctCache`, `window._appVersion`, `window._buildNrsDegree`, `window._canonId`, `window._cvRenderCard`, `window._cvRows`, `window._diag`, `window._dossierRedrawIfNeeded`, `window._dossierRelabel`, `window._ensureMapSettled`, `window._go3D`, `window._hypergraph`, `window._initGeoGlobe`, `window._injectGraphContext`, `window._invalidateNRS`, `window._khSrvBanner`, `window._khipuLoaderDismiss`, `window._khipuLoaderFallback`, `window._khipuScatter`, `window._khipuServerCheck`, `window._lblOn`, `window._liveLoading`, `window._liveRecolorByImpact`, `window._liveResetColors`, `window._liveSelectedNode`, `window._liveTintLinks`, `window._mapLayers`, `window._mapState`, `window._newClientOrderId`, `window._openDossier`, `window._openResearch`, `window._openSecondBrain`, `window._pfPendingAdd`, `window._refreshLiveData`, `window._resizeNodesByCap`, `window._secondBrain`, `window._selectedNode`, `window._showUpdatePill`, `window._simGroundFactor`, `window._termCat`, `window._termChangeTf`, `window._termClearAll`, `window._termClearCell`, `window._termDragStart`, `window._termFilter`, `window._termLoadToFirstEmpty`, `window._termOpenTicker`, `window._termRefreshPrices`, `window._termRelabel`, `window._termSetLayout`, `window._termView`, `window._tickerWarnings`, `window._toggle3D`, `window._toggleColorMode`, `window._tpRefreshAgentStatus`, `window._tpRefreshBlotter`, `window._tpRefreshPositions`, `window._tpRelabel`, `window._tradeErrText`, `window._tradeFetch`, `window._tradeOrderAmbiguous`, `window._tradeOrderId`, `window._tradeOrderIsDup`, `window._tradeOrderResolve`, `window._tradeOrderSettle`, `window._tradePinClear`, `window._tradePinRequired`, `window._tradePinSave`, `window._tradePinStored`, `window._tradeStatusInfo`, `window._updPending`, `window._wrChatSend`, `window.addToPortfolio`, `window.applyVerifiedValuations`, `window.canvasGenerate`, `window.catLabel`, `window.clearStressBtn`, `window.closeDiagnostics`, `window.closePropuestas`, `window.closeRegistro`, `window.closeSistema`, `window.closeTradePanelFn`, `window.computeNRS`, `window.computeNRSBreakdown`, `window.cvCol`, `window.esc`, `window.fetchQuotes`, `window.fillLiveMcap`, `window.fillLiveMeta`, `window.goMap`, `window.initCanvasTab`, `window.initGdelt`, `window.initSimTab`, `window.jumpTo`, `window.khJSON`, `window.khipuGraph3D`, `window.lanzarInvestigacion`, `window.liveCapDot`, `window.loadFredMacro`, `window.loadInvestor13F`, `window.loadLiveQuotes`, `window.loadStockChart`, `window.loadTradeFlows`, `window.nexusCore`, `window.openDiagnostics`, `window.openPropuestas`, `window.openRegistro`, `window.openSistema`, `window.openTradeModal`, `window.openTradePanelFn`, `window.posCancel`, `window.posDel`, `window.posEdit`, `window.posSave`, `window.quoteAge`, `window.quoteAgoText`, `window.quoteExchange`, `window.quoteIsLive`, `window.quotePx`, `window.quoteSrcChip`, `window.quoteSrcName`, `window.refreshStyles`, `window.registerBixbyOrb`, `window.renderDetail`, `window.renderNrsTop10`, `window.runAgentes`, `window.safeUrl`, `window.sectorName`, `window.setBixbyThinking`, `window.setChartMode`, `window.setTradePanelQtyPct`, `window.setTradePanelSide`, `window.settleGraph`, `window.stressBtn`, `window.submitTradePanelOrder`, `window.switchTab`, `window.togglePortfolio`, `window.toggleTradingAgent`, `window.updateTradePanelRisk`

Además declara **250** funciones/constantes de nivel superior en sus bloques inline (globales del navegador): `BASE`, `COLLAPSE_THRESHOLD`, `CRITICAL_WEIGHT`, `DEP_TYPES`, `GEO_REGIONS`, `GEO_REGION_OF`, `I18N`, `LBL_MAX`, `LINK_TYPE_COLORS`, `LIVE_BATCH`, `LT_ORDER`, `MAP_FIRST_ALPHA`, `MAP_POS_KEY`, `MKT`, `SERVER_MODE`, `USER_PORTFOLIOS`, `V8`, `W`, `_DS_SRC`, `_NRS_GEO`, `_NRS_GEO_ALIAS`, `_TERM_ICON`, `_TERM_SEED`, `_TT`, `_afterQuotesMerged`, `_alphaDecay`, `_bcCache`, `_capResizeT`, `_chargeStr`, `_chartModes`, `_deselect`, `_dossier`, `_dossierAddCompare`, `_dossierAutocomplete`, `_dossierLoad`, `_dossierLoadCompany`, `_dossierPickAC`, `_dossierRemove`, `_dossierRenderBadges`, `_dossierRenderPanels`, `_dossierRetry`, `_dossierToWarRoom`, `_dsAlign`, `_dsDrawBalance`, `_dsDrawBars`, `_dsDrawLines`, `_dsEmptyCard`, `_dsFmtB`, `_dsL`, `_dsLast`, `_dsNoData`, `_dsNoSeries`, `_dsSetup`, `_dsTransientCard`, `_dsYears`, `_execTermCmd`, `_filterCache`, `_gdeltInited`, `_initTermCmdBar`, `_lblMinR`, `_ldrSet`, `_liveTick`, `_loaderBar`, `_loaderText`, `_mapBootWaiting`, `_mapCkOpen`, `_mapCkSeen`, `_mapClassicBoot`, `_mapCovered`, `_mapFirstRecipe`, `_mapFirstSettleAsync`, `_mapFitPending`, `_mapFlyPending`, `_mapHint`, `_mapHintEl`, `_mapLaidNow`, `_mapLaidOnce`, `_mapOsExpected`, `_mapPosSave`, `_mapPosSaveSoon`, `_mapPosSaveT`, `_mapPosSeed`, `_mapPost`, `_mapReheat`, `_mapSeeded`, `_mapSettleJob`, `_mapSig`, `_mergeLiveQuote`, `_mergeResult`, `_mixHex`, `_nodeCount`, `_nrsCache`, `_nrsCountry`, `_nrsDegree`, `_nrsTerms`, `_paintGraph`, `_persistQuotes`, `_processMktData`, `_recalcLblMin`, `_refreshStylesCore`, `_renderWarRoom`, `_resizeT`, `_resolveId`, `_runAgentSimTab`, `_runClaudeSim`, `_selectNode`, `_showEventsAlert`, `_simInited`, `_simSetStatus`, `_stockCache`, `_term`, `_termAlpha`, `_termApplyGrid`, `_termBuildSidebar`, `_termFlash`, `_termFmtPct`, `_termFmtPx`, `_termGridClick`, `_termIsPhone`, `_termLoadCell` y 130 más

## Depende de

- [[engine.aispend.js]] — usa `KhipuSpend`
- [[engine.canvas-data.js]] — usa `canvasEnrichData`
- [[engine.clients.js]] — usa `KhipuClients`
- [[engine.cockpit.js]] — usa `BixbyCockpit`
- [[engine.command_center.js]] — usa `BixbyCC`
- [[engine.committee.js]] — usa `KhipuCommittee`
- [[engine.crypto.js]] — usa `KhipuCrypto`
- [[engine.explain.js]] — usa `explainChip`, `explainMetric`
- [[engine.fincard.js]] — usa `openFinCard`
- [[engine.graph3d.js]] — usa `KhipuGraph3D`, `_graph3d_updateLiveColors`
- [[engine.guide.js]] — usa `initGuiaTab`
- [[engine.hypergraph.js]] — usa `TemporalHypergraph`
- [[engine.insights.js]] — usa `renderInsightsHistory`, `renderKhipuInsights`
- [[engine.localcharts.js]] — usa `KhipuLocalCharts`
- [[engine.maptime.js]] — usa `KhipuMapTime`, `_mapTimePaint`
- [[engine.matrixview.js]] — usa `renderMatrixView`
- [[engine.mcpconnect.js]] — usa `KhipuMCP`
- [[engine.portfolios.js]] — usa `KhipuPortfolios`
- [[engine.reconcile.js]] — usa `KhipuReconcile`
- [[engine.research.js]] — usa `KhipuResearch`
- [[engine.resolve.js]] — usa `KhipuResolve`, `_surface`
- [[engine.riskreport.js]] — usa `KhipuRisk`
- [[engine.secondbrain.js]] — usa `SecondBrain`
- [[engine.spacemonitor.js]] — usa `KhipuSpace`
- [[engine.statematrix.js]] — usa `KhipuState`
- [[engine.temporal-graph.js]] — usa `initTKGTab`
- [[engine.termdata.js]] — usa `TermData`
- [[engine.toast.js]] — usa `KhipuToast`, `khipuActor`
- [[engine.universe2d.js]] — usa `KhipuUniverse2D`
- [[engine.voice.js]] — usa `BixbyVoice`
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
- [[sim.scenario_builder.js]] — usa `ScenarioBuilder`, `buildLiveReportContext`
- [[engine.graph3d.js]] — lo nombra por su ruta
- [[engine.hypergraph.js]] — lo nombra por su ruta
- [[sw.js]] — lo nombra por su ruta

## Lo usan

- [[engine.aispend.js]] — usa `BASE`, `LANG`, `_tradeFetch`
- [[engine.brief.js]] — usa `LANG`, `MKT`, `NODE_BY_ID`, `computeDownstream`, `computeNRS`, `jumpTo`, `switchTab`
- [[engine.canvas-data.js]] — usa `BASE`
- [[engine.clients.js]] — usa `LANG`, `_tradeFetch`, `_tradePinStored`
- [[engine.cockpit.js]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `_cvRenderCard`, `_ensureMapSettled`, `_go3D`, `_liveRecolorByImpact` y 21 más
- [[engine.command_center.js]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `_cvRenderCard`, `_openSecondBrain`, `activateStress`, `canvasGenerate` y 4 más
- [[engine.committee.js]] — usa `BASE`, `LANG`, `NODE_BY_ID`, `_tradeFetch`, `_tradePinStored`, `safeUrl`
- [[engine.compare.js]] — usa `LANG`, `LINKS`, `NODE_BY_ID`, `computeNRS`, `computeNRSBreakdown`, `sectorName`
- [[engine.crypto.js]] — usa `LANG`, `_tradeErrText`, `_tradeFetch`, `_tradeOrderAmbiguous`, `_tradeOrderId`, `_tradeOrderIsDup`, `_tradeOrderSettle`, `_tradePinStored` y 1 más
- [[engine.desktop.js]] — usa `LANG`
- [[engine.explain.js]] — usa `LANG`
- [[engine.fincard.js]] — usa `BASE`, `LANG`, `NODE_BY_ID`, `_openDossier`
- [[engine.globe.js]] — usa `BASE`, `LINKS`, `computeNRS`
- [[engine.graph3d.js]] — usa `LINKS`, `NODE_BY_ID`, `_diag`, `_tickerWarnings`, `computeNRS`, `computeNodeRadius`, `getCatColorHex`, `getLinkColorHex` y 4 más
- [[engine.guide.js]] — usa `LANG`, `LINKS`, `NODE_BY_ID`
- [[engine.hypergraph.js]] — usa `DataLayer`, `NODE_BY_ID`, `getCatColorHex`
- [[engine.insights.js]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `activateStress`, `computeDownstream`, `computeNRS` y 3 más
- [[engine.khipu_chat.js]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `_liveSelectedNode`, `_selectedNode`, `activeTab`, `jumpTo` y 3 más
- [[engine.khipu_lang.js]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `_tradeErrText`, `_tradeFetch`, `switchTab`
- [[engine.layers.js]] — usa `LANG`
- [[engine.live.js]] — usa `BASE`, `LANG`, `MKT`, `_appVersion`, `_invalidateNRS`, `_showUpdatePill`, `_tradeFetch`
- [[engine.livesim.js]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `_liveRecolorByImpact`, `_liveResetColors`, `_liveSelectedNode`, `_liveTintLinks` y 3 más
- [[engine.localcharts.js]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `_selectedNode`, `computeNRS`, `computeNRSBreakdown` y 3 más
- [[engine.maptime.js]] — usa `LANG`, `LINKS`, `NODE_BY_ID`, `_mapLayers`, `computeNodeRadius`, `getLinkColorHex`, `jumpTo`, `refreshStyles` y 2 más
- [[engine.mascot.js]] — usa `LANG`
- [[engine.matrixview.js]] — usa `LANG`, `LINKS`, `NODE_BY_ID`, `sectorName`
- [[engine.mcpconnect.js]] — usa `LANG`, `_tradeFetch`, `closeSistema`
- [[engine.nav4.js]] — usa `activeTab`, `switchTab`
- [[engine.orb.js]] — usa `LANG`
- [[engine.oswindows.js]] — usa `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `_canonId`, `loadLiveQuotes`, `quoteAge`, `quoteAgoText` y 3 más
- [[engine.pfcommittee.js]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `_tradeFetch`
- [[engine.pfreports.js]] — usa `BASE`, `LANG`, `safeUrl`
- [[engine.pickers.js]] — usa `LANG`, `NODE_BY_ID`
- [[engine.portfolios.js]] — usa `LANG`, `MKT`, `NODE_BY_ID`, `fetchQuotes`
- [[engine.reconcile.js]] — usa `BASE`, `LANG`, `_tradeFetch`
- [[engine.research.js]] — usa `BASE`, `LANG`, `NODE_BY_ID`, `jumpTo`
- [[engine.resolve.js]] — usa `LANG`, `NODE_BY_ID`, `_openSecondBrain`, `_termOpenTicker`, `activateStress`, `canvasGenerate`, `closeSistema`, `jumpTo` y 3 más
- [[engine.riskreport.js]] — usa `BASE`, `DataLayer`, `LANG`, `MKT`, `NODE_BY_ID`
- [[engine.secondbrain.js]] — usa `DataLayer`, `LANG`, `LINKS`, `NODE_BY_ID`, `NRS_FLOW_TYPES`, `V8detail`, `_secondBrain`, `activateStress` y 13 más
- [[engine.spacemonitor.js]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `computeNRS`, `jumpTo`, `quotePx` y 1 más
- [[engine.statematrix.js]] — usa `LINKS`, `MKT`, `computeNRS`
- [[engine.sync.js]] — usa `BASE`, `MKT`, `renderMarket`
- [[engine.temporal-graph.js]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `SERVER_MODE`, `_tradeErrText`, `_tradeFetch` y 7 más
- [[engine.termdata.js]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `_termOpenTicker`, `computeNRS`, `fillLiveMeta` y 2 más
- [[engine.timeline3d.js]] — usa `LANG`, `NODE_BY_ID`, `getLinkColorHex`
- [[engine.toast.js]] — usa `LANG`, `_tradeFetch`, `_tradeStatusInfo`
- [[engine.universe2d.js]] — usa `LANG`, `_diag`, `computeNRS`, `computeNodeRadius`, `getCatColorHex`, `jumpTo`
- [[engine.voice.js]] — usa `BASE`, `KhipuLive`, `LANG`, `LINKS`, `NODE_BY_ID`, `NRS_FLOW_TYPES`, `_canonId`, `_liveRecolorByImpact` y 21 más
- [[engine.worldmonitor.js]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `computeNRS`, `goMap`, `nexusCore` y 1 más
- [[engine.xray.js]] — usa `DataLayer`, `KhipuLive`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `_openSecondBrain`, `activateStress` y 10 más
- [[sim.scenario_builder.js]] — usa `BASE`, `NODE_BY_ID`, `quotePx`
- [[server.py]] — lo nombra por su ruta

## Endpoints que llama

- `DELETE /api/ontology/alerts/<alert_id>` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/candles/<ticker>` → [[server.py]] ([[API candles]])
- `GET /api/company/live/<ticker>` → [[server.py]] ([[API company]])
- `GET /api/company/research/<ticker>` → [[server.py]] ([[API company]])
- `GET /api/diagnostics` → [[server.py]] ([[API diagnostics]])
- `GET /api/dossier/<ticker>` → [[server.py]] ([[API dossier]])
- `GET /api/earnings/<ticker>` → [[server.py]] ([[API earnings]])
- `GET /api/fundamentals/<ticker>` → [[server.py]] ([[API fundamentals]])
- `GET /api/health` → [[server.py]] ([[API health]])
- `GET /api/insiders/<ticker>` → [[server.py]] ([[API insiders]])
- `GET /api/investors/13f/<ticker>` → [[server.py]] ([[API investors]])
- `GET /api/ipo_calendar` → [[server.py]] ([[API ipo_calendar]])
- `GET /api/macro/fred` → [[server.py]] ([[API macro]])
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
- `GET /api/supply-chain/trade-flows` → [[server.py]] ([[API supply-chain]])
- `GET /api/trade/account` → [[server.py]] ([[API trade]])
- `GET /api/trade/agent/status` → [[server.py]] ([[API trade]])
- `GET /api/trade/history` → [[server.py]] ([[API trade]])
- `GET /api/trade/positions/detail` → [[server.py]] ([[API trade]])
- `GET /api/trade/status` → [[server.py]] ([[API trade]])
- `GET /api/ws-token` → [[server.py]] ([[API ws-token]])
- `POST /api/ai/analyze` → [[server.py]] ([[API ai]])
- `POST /api/canvas/generate` → [[server.py]] ([[API canvas]])
- `POST /api/diag` → [[server.py]] ([[API diag]])
- `POST /api/matrix/factor/fire` → [[matrix.api.py]] ([[API matrix]])
- `POST /api/news/portfolio` → [[core.portfolio_reports_api.py]] ([[API news]])
- `POST /api/ontology/agents/investigar` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/agents/proposals/<proposal_id>/approve` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/agents/proposals/<proposal_id>/reject` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/agents/run` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/ingest/news` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/portfolio-risk` → [[server.py]] ([[API portfolio-risk]])
- `POST /api/quotes/live` → [[server.py]] ([[API quotes]])
- `POST /api/sim/agents` → [[server.py]] ([[API sim]])
- `POST /api/trade/agent/start` → [[server.py]] ([[API trade]])
- `POST /api/trade/agent/stop` → [[server.py]] ([[API trade]])
- `POST /api/trade/order` → [[server.py]] ([[API trade]])
- `POST /api/ws-key` → [[server.py]] ([[API ws-key]])
- `POST /v1/auth/key` → [[server.py]] ([[API v1 (pública)]])

## Pruebas que lo cubren

- [[tests.test_agents_registry.py]]
- [[tests.test_canvas_charts.py]]
- [[tests.test_cleanup_client.py]]
- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_cleanup_modules_theme_i18n.py]]
- [[tests.test_cleanup_nrs_parity.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_client_hardening.py]]
- [[tests.test_docs_facts.py]]
- [[tests.test_khipus_os_fixes_shell.py]]
- [[tests.test_khipus_os_integration.py]]
- [[tests.test_khipus_os_perf.py]]
- [[tests.test_khipus_os_shell.py]]
- [[tests.test_live_labels_misc.py]]
- [[tests.test_map_search_reset.py]]
- [[tests.test_overnight2_fixer_review.py]]
- [[tests.test_overnight2_sistema_shell.py]]
- [[tests.test_overnight3_diag_bilingual.py]]
- [[tests.test_overnight3_toast_tokens.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_verified_valuations.py]]
- [[tests.test_voice_os_client.py]]
- [[tests.test_voice_tour.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 (b) — LIMPIEZA QUE NO QUEDEN COSAS SUELTAS (sw v254)]]
- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-10-06 (ii) — KHIPUS OS v1 (sw v245)]]
- [[Sesión 2026-10-06 (hh) — CANVAS NIVEL POWER BI - COLOR VALIDADO + INTERACCIÓN (sw v244)]]
- [[Sesión 2026-10-05 (bb) — SIMULACIÓN IA SIMPLE CON DATOS EN VIVO (sw v235)]]
- [[Sesión 2026-10-05 (aa) — FUNDAMENTALES EN VIVO DE TODO EL GRAFO (sw v234)]]
- [[Sesión 2026-10-05 (y) — NRS ACOTADO + BÚSQUEDA DEL MAPA (sw v232)]]
- [[Sesión 2026-10-05 (x) — CIFRAS VIEJAS - VERIFICADAS - EN VIVO (sw v231)]]
- [[Sesión 2026-10-04 — ESCRITORIO KHIPU K1 - VENTANAS DENTRO DE LA CABINA (sw v186)]]
- [[Sesión 2026-10-03 (f) — PANEL DE TRADING BILINGÜE Y MÓVIL + APROBACIÓN DEL COMITÉ CON]]
- [[Sesión 2026-10-03 (c) — TERMINAL REDISEÑADA + POP-UPS DE COMPRA-VENTA (sw v182)]]

_…y 13 sesiones más antiguas._
