---
tipo: "pagina"
capa: "Interfaz (Khipus OS)"
ruta: "app.html"
lenguaje: "html"
lineas: 3537
aliases: ["app.html"]
tags: ["capa/interfaz", "tipo/pagina"]
---

# app.html

> Página · capa [[Capa Interfaz (Khipus OS)]] · 3.537 líneas · `app.html`

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
2. [[nodes.nodes_seed.js]] (línea 1504)
3. [[nodes.categories_extra.js]] (línea 1505)
4. [[nodes.nodes_expand.js]] (línea 1506)
5. [[nodes.nodes_expand2.js]] (línea 1507)
6. [[nodes.nodes_spacex.js]] (línea 1508)
7. [[nodes.nodes_expand3.js]] (línea 1509)
8. [[nodes.nodes_nuclear.js]] (línea 1510)
9. [[nodes.nodes_expand4.js]] (línea 1511)
10. [[nodes.nodes_expand5.js]] (línea 1512)
11. [[nodes.meta_fill.js]] (línea 1513)
12. [[nodes.nodes_china.js]] (línea 1514)
13. [[nodes.nodes_multicapa.js]] (línea 1515)
14. [[nodes.preipo_intel.js]] (línea 1516)
15. [[nodes.listing_status.js]] (línea 1517)
16. [[nodes.private_valuations.js]] (línea 1518)
17. [[nodes.links_all.js]] (línea 1519)
18. [[nodes.links_expand.js]] (línea 1520)
19. [[nodes.links_connect.js]] (línea 1521)
20. [[nodes.merge_graph.js]] (línea 1522)
21. [[engine.catalog_sync.js]] (línea 1523)
22. `vendor/three.min.js` — externo/vendor (línea 1524)
23. `vendor/chart.umd.min.js` — externo/vendor (línea 1525)
24. `vendor/satellite.min.js` — externo/vendor (línea 1526)
25. bloque `<script>` inline #1 (línea 1552, 341 líneas)
26. [[engine.pfstore.js]] (línea 2681)
27. [[engine.app_main.js]] (línea 2682)
28. bloque `<script>` inline #2 (línea 2967, 119 líneas)
29. [[engine.loading.js]] (línea 3088)
30. [[engine.toast.js]] (línea 3089)
31. [[engine.hotclient.js]] (línea 3090)
32. [[engine.agents_registry.js]] (línea 3091)
33. [[engine.tour_script.js]] (línea 3092)
34. [[engine.mascot.js]] (línea 3093)
35. [[engine.universe2d.js]] (línea 3094)
36. [[engine.resolve.js]] (línea 3095)
37. [[engine.orb.js]] (línea 3096)
38. [[engine.trade.js]] (línea 3097)
39. [[engine.voice.js]] (línea 3098)
40. [[engine.secondbrain.js]] (línea 3099)
41. [[engine.geo_coords.js]] (línea 3100)
42. [[engine.globe.js]] (línea 3101)
43. [[engine.canvas-data.js]] (línea 3102)
44. [[nodes.temporal_seed_facts.js]] (línea 3103)
45. [[nodes.temporal_seed_facts2.js]] (línea 3104)
46. [[nodes.ontology.js]] (línea 3105)
47. [[nodes.ontology_facts.js]] (línea 3106)
48. [[nodes.legal_names.js]] (línea 3107)
49. [[engine.temporal-graph.js]] (línea 3108)
50. [[engine.timeline3d.js]] (línea 3109)
51. [[engine.maptime.js]] (línea 3110)
52. [[engine.khipu_lang.js]] (línea 3111)
53. [[engine.guide.js]] (línea 3112)
54. [[engine.xray.js]] (línea 3113)
55. [[engine.research.js]] (línea 3114)
56. bloque `<script>` inline #3 (línea 3115, 52 líneas)
57. [[engine.riskreport.js]] (línea 3167)
58. [[engine.worldmonitor.js]] (línea 3168)
59. [[engine.spacemonitor.js]] (línea 3169)
60. [[engine.pickers.js]] (línea 3170)
61. [[engine.committee.js]] (línea 3171)
62. [[engine.aispend.js]] (línea 3172)
63. [[engine.pfcommittee.js]] (línea 3173)
64. [[engine.pfreports.js]] (línea 3174)
65. [[engine.sync.js]] (línea 3175)
66. [[engine.clients.js]] (línea 3176)
67. [[engine.mcpconnect.js]] (línea 3177)
68. bloque `<script>` inline #4 (línea 3178, 16 líneas)
69. [[engine.insights.js]] (línea 3194)
70. [[engine.statematrix.js]] (línea 3195)
71. [[engine.livesim.js]] (línea 3196)
72. [[engine.layers.js]] (línea 3197)
73. [[engine.brief.js]] (línea 3198)
74. [[engine.compare.js]] (línea 3199)
75. [[engine.matrixview.js]] (línea 3200)
76. [[engine.nav4.js]] (línea 3201)
77. [[engine.localcharts.js]] (línea 3202)
78. [[engine.fincard.js]] (línea 3203)
79. [[engine.termdata.js]] (línea 3204)
80. [[engine.explain.js]] (línea 3205)
81. [[engine.reconcile.js]] (línea 3206)
82. [[engine.governance.js]] (línea 3207)
83. [[engine.audit.js]] (línea 3208)
84. [[engine.pricehist.js]] (línea 3209)
85. [[nodes.crypto_intel.js]] (línea 3210)
86. [[nodes.crypto_intel2.js]] (línea 3211)
87. [[engine.crypto.js]] (línea 3212)
88. [[engine.portfolios.js]] (línea 3213)
89. [[engine.genui.js]] (línea 3216)
90. [[engine.oswindows.js]] (línea 3217)
91. [[engine.khipu_chat.js]] (línea 3218)
92. [[engine.desktop.js]] (línea 3219)
93. [[engine.cockpit.js]] (línea 3220)
94. [[engine.live.js]] (línea 3221)
95. [[engine.command_center.js]] (línea 3222)
96. [[sim.scenario_builder.js]] (línea 3223)
97. [[engine.app_coordinator.js]] (línea 3225)
98. [[engine.app_trade_panel.js]] (línea 3526)
99. [[engine.app_preflight.js]] (línea 3529)
100. [[engine.app_canvas.js]] (línea 3532)
101. [[engine.app_scatter.js]] (línea 3534)

## Bloques `<script>` inline

| # | Línea | Líneas | Funciones | Cabecera |
|---|---|---|---|---|
| 1 | 1552 | 341 | 11 | Hard fallback: always dismiss \#boot after 3s even if main JS crashes |
| 2 | 2967 | 119 | 4 | Lissajous spirograph — same math renders at any size |
| 3 | 3115 | 52 | 3 | AVISO "SERVIDOR NO DISPONIBLE" (incidente 2026-09-29: Railway dejó de responder y la app mostraba EN SILENCIO la última versión guardada por el service worker … |
| 4 | 3178 | 16 | 1 | Insignia en 👥 Clientes: propuestas (de agentes MCP o del comité) esperando aprobación humana. Nunca pide el PIN (pendingCount devuelve null sin PIN). |

## API pública (globales window.* que define)

`window.BixbyVoice`, `window.__khStaleReloaded`, `window._khSrvBanner`, `window._khipuServerCheck`, `window._newClientOrderId`, `window._tradeErrText`, `window._tradeFetch`, `window._tradeOrderAmbiguous`, `window._tradeOrderId`, `window._tradeOrderIsDup`, `window._tradeOrderResolve`, `window._tradeOrderSettle`, `window._tradePinClear`, `window._tradePinRequired`, `window._tradePinSave`, `window._tradePinStored`, `window._tradeStatusInfo`, `window.khJSON`, `window.registerBixbyOrb`, `window.safeUrl`, `window.setBixbyThinking`

## Depende de

- [[engine.app_canvas.js]] — usa `canvasGenerate`
- [[engine.app_coordinator.js]] — usa `_dossierAddCompare`, `_dossierAutocomplete`, `_dossierLoad`, `_dossierToWarRoom`, `_go3D`, `_termCat`, `_termClearAll`, `_termFilter`, `_termSetLayout`, `_termView`
- [[engine.app_main.js]] — usa `BASE`, `LANG`, `_injectGraphContext`, `_showUpdatePill`, `closeSistema`, `lanzarInvestigacion`, `loadCorporateEvents`, `openDiagnostics`, `openPropuestas`, `openRegistro` y 3 más
- [[engine.app_trade_panel.js]] — usa `_tpRefreshAgentStatus`, `_tpRefreshBlotter`, `_tpRefreshPositions`, `closeTradePanelFn`, `setTradePanelQtyPct`, `setTradePanelSide`, `submitTradePanelOrder`, `toggleTradingAgent`, `updateTradePanelRisk`
- [[engine.clients.js]] — usa `KhipuClients`
- [[engine.cockpit.js]] — usa `BixbyCockpit`
- [[engine.command_center.js]] — usa `BixbyCC`
- [[engine.committee.js]] — usa `KhipuCommittee`
- [[engine.explain.js]] — usa `explainMetric`
- [[engine.riskreport.js]] — usa `KhipuRisk`
- [[engine.toast.js]] — usa `KhipuToast`
- [[engine.voice.js]] — usa `BixbyVoice`

## Lo usan

- [[engine.aispend.js]] — usa `_tradeFetch`
- [[engine.app_coordinator.js]] — usa `safeUrl`
- [[engine.app_main.js]] — usa `_tradeErrText`, `_tradeFetch`, `khJSON`, `safeUrl`
- [[engine.app_trade_panel.js]] — usa `_tradeErrText`, `_tradeFetch`, `_tradeOrderAmbiguous`, `_tradeOrderId`, `_tradeOrderIsDup`, `_tradeOrderResolve`, `_tradeOrderSettle`, `_tradeStatusInfo`
- [[engine.audit.js]] — usa `_tradeFetch`, `_tradePinStored`
- [[engine.clients.js]] — usa `_tradeFetch`, `_tradePinStored`
- [[engine.cockpit.js]] — usa `_tradeErrText`, `_tradeFetch`, `_tradePinSave`, `_tradePinStored`, `_tradeStatusInfo`, `registerBixbyOrb`, `setBixbyThinking`
- [[engine.committee.js]] — usa `_tradeFetch`, `_tradePinStored`, `safeUrl`
- [[engine.crypto.js]] — usa `_tradeErrText`, `_tradeFetch`, `_tradeOrderAmbiguous`, `_tradeOrderId`, `_tradeOrderIsDup`, `_tradeOrderSettle`, `_tradePinStored`
- [[engine.genui.js]] — usa `safeUrl`
- [[engine.governance.js]] — usa `_tradeFetch`
- [[engine.importer.js]] — usa `_tradeFetch`
- [[engine.khipu_chat.js]] — usa `safeUrl`
- [[engine.khipu_lang.js]] — usa `_tradeErrText`, `_tradeFetch`
- [[engine.live.js]] — usa `_tradeFetch`
- [[engine.mcpconnect.js]] — usa `_tradeFetch`
- [[engine.pfcommittee.js]] — usa `_tradeFetch`
- [[engine.pfreports.js]] — usa `safeUrl`
- [[engine.pricehist.js]] — usa `_tradeFetch`
- [[engine.reconcile.js]] — usa `_tradeFetch`
- [[engine.secondbrain.js]] — usa `safeUrl`
- [[engine.temporal-graph.js]] — usa `_tradeErrText`, `_tradeFetch`, `safeUrl`
- [[engine.toast.js]] — usa `_tradeFetch`, `_tradeStatusInfo`
- [[engine.trade.js]] — usa `_tradeErrText`, `_tradeFetch`, `_tradeOrderAmbiguous`, `_tradeOrderId`, `_tradeOrderIsDup`, `_tradeOrderSettle`
- [[engine.voice.js]] — usa `_tradeFetch`, `_tradeStatusInfo`, `setBixbyThinking`
- [[scripts.build_categories.py]] — lo nombra por su ruta
- [[server.py]] — lo nombra por su ruta

## Endpoints que llama

- `GET /api/health` → [[server.py]] ([[API health]])
- `GET /api/trade/status` → [[server.py]] ([[API trade]])

## Pruebas que lo cubren

- [[tests._app_source.py]]
- [[tests.test_app_split.py]]
- [[tests.test_catalog_api_client.py]]
- [[tests.test_catalog_fix_categories.py]]
- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_client_hardening.py]]
- [[tests.test_csp_estricta.py]]
- [[tests.test_docs_facts.py]]
- [[tests.test_genui_client_static.py]]
- [[tests.test_genui_f3_client_static.py]]
- [[tests.test_import_panel_browser.py]]
- [[tests.test_import_panel_static.py]]
- [[tests.test_khipus_os_fixes_shell.py]]
- [[tests.test_khipus_os_integration.py]]
- [[tests.test_khipus_os_shell.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_one_portfolio_store.py]]
- [[tests.test_voice_tour.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (m) — app.html PARTIDO + 2 arreglos visibles — sw v268]]
- [[Sesión 2026-10-13 (l) — APP.HTML PARTIDO SIN CAMBIAR NADA (G5-06) — sw v267]]
- [[Sesión 2026-10-13 (k) — FASE 2+ LOTE I - rutas con decisión, CSP estricta, riesgo]]
- [[Sesión 2026-10-11 (b) — LIMPIEZA QUE NO QUEDEN COSAS SUELTAS (sw v254)]]
- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-10-06 (ii) — KHIPUS OS v1 (sw v245)]]
- [[Sesión 2026-10-06 (hh) — CANVAS NIVEL POWER BI - COLOR VALIDADO + INTERACCIÓN (sw v244)]]
- [[Sesión 2026-10-05 (bb) — SIMULACIÓN IA SIMPLE CON DATOS EN VIVO (sw v235)]]
- [[Sesión 2026-10-05 (aa) — FUNDAMENTALES EN VIVO DE TODO EL GRAFO (sw v234)]]
- [[Sesión 2026-10-05 (y) — NRS ACOTADO + BÚSQUEDA DEL MAPA (sw v232)]]
- [[Sesión 2026-10-05 (x) — CIFRAS VIEJAS - VERIFICADAS - EN VIVO (sw v231)]]

_…y 16 sesiones más antiguas._
