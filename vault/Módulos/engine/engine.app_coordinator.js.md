---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/app_coordinator.js"
lenguaje: "javascript"
lineas: 2703
aliases: ["engine/app_coordinator.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/app_coordinator.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 2.703 líneas · `engine/app_coordinator.js`

## Para qué sirve

Khipu Core Coordinator

## API pública (globales que define)

`window._diag`, `window._dossierRedrawIfNeeded`, `window._dossierRelabel`, `window._go3D`, `window._hypergraph`, `window._openDossier`, `window._openResearch`, `window._openSecondBrain`, `window._secondBrain`, `window._simGroundFactor`, `window._termCat`, `window._termChangeTf`, `window._termClearAll`, `window._termClearCell`, `window._termDragStart`, `window._termFilter`, `window._termLoadToFirstEmpty`, `window._termOpenTicker`, `window._termRefreshPrices`, `window._termRelabel`, `window._termSetLayout`, `window._termView`, `window._toggle3D`, `window._wrChatSend`, `window.catLabel`, `window.computeNRS`, `window.fetchQuotes`, `window.initGdelt`, `window.khipuGraph3D`, `window.loadFredMacro`, `window.loadInvestor13F`, `window.loadTradeFlows`, `window.nexusCore`, `window.renderDetail`, `window.renderNrsTop10`, `window.switchTab`

De nivel superior (globales del script): `_DS_SRC`, `_TERM_ICON`, `_TERM_SEED`, `_TT`, `_dossier`, `_dossierAddCompare`, `_dossierAutocomplete`, `_dossierLoad`, `_dossierLoadCompany`, `_dossierPickAC`, `_dossierRemove`, `_dossierRenderBadges`, `_dossierRenderPanels`, `_dossierRetry`, `_dossierToWarRoom`, `_dsAlign`, `_dsDrawBalance`, `_dsDrawBars`, `_dsDrawLines`, `_dsEmptyCard`, `_dsFmtB`, `_dsL`, `_dsLast`, `_dsNoData`, `_dsNoSeries`, `_dsSetup`, `_dsTransientCard`, `_dsYears`, `_execTermCmd`, `_gdeltInited`, `_initTermCmdBar`, `_renderWarRoom`, `_runAgentSimTab`, `_runClaudeSim`, `_simInited`, `_simSetStatus`, `_term`, `_termAlpha`, `_termApplyGrid`, `_termBuildSidebar`, `_termFlash`, `_termFmtPct`, `_termFmtPx`, `_termGridClick`, `_termIsPhone`, `_termLoadCell`, `_termMakeCell`, `_termMarkOpen`, `_termOpenFromList`, `_termPaintQuote`, `_termQuote`, `_termRecolor`, `_termRenderList`, `_termSectorOf`, `_termSeed`, `_termTok`, `_tt`, `_wrAnimId`, `_wrComputeLayout`, `_wrFallbackCascade`, `_wrFinish`, `_wrRenderAgents`, `_wrRenderPrices`, `_wrRenderWinners`, `_wrReportText`, `_wrRoundIvl`, `_wrStartAnimation`, `initKhipuCore`, `initLiveData`, `initSimTab`, `initSpaceTab`, `initTerminalTab`

## Depende de

- [[app.html]] — usa `safeUrl`
- [[engine.app_main.js]] — usa `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `_appVersion`, `_liveLoading`, `activeTab`, `applyLang`, `catLabel`, `computeNRS` y 14 más
- [[engine.app_scatter.js]] — usa `_khipuScatter`
- [[engine.app_trade_panel.js]] — usa `openTradeModal`
- [[engine.explain.js]] — usa `explainChip`
- [[engine.fincard.js]] — usa `openFinCard`
- [[engine.graph3d.js]] — usa `KhipuGraph3D`
- [[engine.hypergraph.js]] — usa `TemporalHypergraph`
- [[engine.resolve.js]] — usa `KhipuResolve`, `_surface`
- [[engine.secondbrain.js]] — usa `SecondBrain`
- [[engine.spacemonitor.js]] — usa `KhipuSpace`
- [[engine.termdata.js]] — usa `TermData`
- [[engine.toast.js]] — usa `KhipuToast`
- [[engine.universe2d.js]] — usa `KhipuUniverse2D`
- [[nodes.nodes_seed.js]] — usa `CAT_TO_SECTOR`, `NODES`, `SECTORS9`
- [[sim.scenario_builder.js]] — usa `ScenarioBuilder`, `buildLiveReportContext`
- [[engine.graph3d.js]] — lo nombra por su ruta
- [[engine.hypergraph.js]] — lo nombra por su ruta

Se carga en [[app.html]] en la posición **98 de 102** (línea 3226), después de [[sim.scenario_builder.js]] y antes de [[engine.app_trade_panel.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 98)
- [[app.html]] — usa `_dossierAddCompare`, `_dossierAutocomplete`, `_dossierLoad`, `_dossierToWarRoom`, `_go3D`, `_termCat`, `_termClearAll`, `_termFilter` y 2 más
- [[engine.app_main.js]] — usa `_dossierRedrawIfNeeded`, `_dossierRelabel`, `_termRefreshPrices`, `initGdelt`, `initSimTab`, `initSpaceTab`, `initTerminalTab`, `renderNrsTop10`
- [[engine.app_preflight.js]] — usa `initSimTab`
- [[engine.app_scatter.js]] — usa `_toggle3D`
- [[engine.cockpit.js]] — usa `_go3D`, `_termOpenTicker`, `initSimTab`, `initSpaceTab`, `initTerminalTab`
- [[engine.command_center.js]] — usa `_openSecondBrain`, `nexusCore`
- [[engine.fincard.js]] — usa `_openDossier`
- [[engine.graph3d.js]] — usa `_diag`, `khipuGraph3D`
- [[engine.khipu_chat.js]] — usa `nexusCore`
- [[engine.resolve.js]] — usa `_openSecondBrain`, `_termOpenTicker`
- [[engine.secondbrain.js]] — usa `_secondBrain`, `nexusCore`
- [[engine.termdata.js]] — usa `_termOpenTicker`
- [[engine.universe2d.js]] — usa `_diag`
- [[engine.voice.js]] — usa `_openSecondBrain`, `_termOpenTicker`, `khipuGraph3D`
- [[engine.worldmonitor.js]] — usa `nexusCore`
- [[engine.xray.js]] — usa `_openSecondBrain`

## Endpoints que llama

- `GET /api/candles/<ticker>` → [[server.py]] ([[API candles]])
- `GET /api/company/research/<ticker>` → [[server.py]] ([[API company]])
- `GET /api/dossier/<ticker>` → [[server.py]] ([[API dossier]])
- `GET /api/fundamentals/<ticker>` → [[server.py]] ([[API fundamentals]])
- `GET /api/investors/13f/<ticker>` → [[server.py]] ([[API investors]])
- `GET /api/macro/fred` → [[server.py]] ([[API macro]])
- `GET /api/news/<ticker>` → [[server.py]] ([[API news]])
- `GET /api/news/gdelt/<company_name>` → [[server.py]] ([[API news]])
- `GET /api/supply-chain/trade-flows` → [[server.py]] ([[API supply-chain]])
- `POST /api/ai/analyze` → [[server.py]] ([[API ai]])
- `POST /api/diag` → [[server.py]] ([[API diag]])
- `POST /api/matrix/factor/fire` → [[matrix.api.py]] ([[API matrix]])
- `POST /api/portfolio-risk` → [[server.py]] ([[API portfolio-risk]])
- `POST /api/sim/agents` → [[server.py]] ([[API sim]])

## Pruebas que lo cubren

- [[tests.test_app_split.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (m) — app.html PARTIDO + 2 arreglos visibles — sw v268]]
- [[Sesión 2026-10-13 (l) — APP.HTML PARTIDO SIN CAMBIAR NADA (G5-06) — sw v267]]
