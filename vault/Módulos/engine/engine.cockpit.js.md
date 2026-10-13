---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/cockpit.js"
lenguaje: "javascript"
lineas: 5007
aliases: ["engine/cockpit.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/cockpit.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 5.007 líneas · `engine/cockpit.js`

## Para qué sirve

CABINA DE BIXBY · el modo pantalla completa Khipu deja de ser un botón: SE VUELVE la pantalla. - Arriba: el orbe/logo de Khipu + estado (escuchando / pensando / listo) + una barra para pedirle cosas por texto o por voz (🎙). - Abajo: un ESCENARIO grande (un lienzo) donde Khipu te muestra lo que pidas: · la radiografía completa de una empresa (X-Ray a pantalla completa) · una simulación de shock (a quién arrastra / quién gana) · dos empresas comparadas lado a lado · un gráfico / tabla generado por IA (Canvas) · o un lienzo en blanco Voz y texto van al MISMO escenario: cuando Khipu (por voz) abre un X-Ray, xray.js detecta que la cabina está abierta y lo pinta aquí, no en el …

## API pública (globales que define)

`window.BixbyCockpit`, `window.__kosKindQueue`, `window._cockpitMapSim`, `window._computePortfolioSummary`, `window._openBrokerConfirm`, `window._openDeepResearch`, `window._parseTradeCommand`, `window._runAgentSim`

## Depende de

- [[app.html]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `_cvRenderCard`, `_ensureMapSettled`, `_go3D`, `_liveRecolorByImpact`, `_liveSelectedNode`, `_termOpenTicker` y 19 más
- [[engine.brief.js]] — usa `_briefOpen`
- [[engine.canvas-data.js]] — usa `canvasEnrichData`
- [[engine.clients.js]] — usa `KhipuClients`
- [[engine.committee.js]] — usa `KhipuCommittee`
- [[engine.crypto.js]] — usa `KhipuCrypto`
- [[engine.desktop.js]] — usa `KhipuDesk`
- [[engine.explain.js]] — usa `explainMetric`
- [[engine.fincard.js]] — usa `openFinCard`
- [[engine.guide.js]] — usa `initGuiaTab`
- [[engine.khipu_chat.js]] — usa `KhipuChat`
- [[engine.khipu_lang.js]] — usa `KHIPU`
- [[engine.loading.js]] — usa `KhipuLoading`
- [[engine.localcharts.js]] — usa `KhipuLocalCharts`
- [[engine.mascot.js]] — usa `KhipuAgentPrefs`, `KhipuMascot`
- [[engine.mcpconnect.js]] — usa `KhipuMCP`
- [[engine.orb.js]] — usa `BixbyOrb`
- [[engine.oswindows.js]] — usa `KhipuOSWin`
- [[engine.pickers.js]] — usa `KhipuPick`
- [[engine.portfolios.js]] — usa `KhipuPortfolios`
- [[engine.research.js]] — usa `KhipuResearch`
- [[engine.resolve.js]] — usa `KhipuResolve`, `_surface`
- [[engine.riskreport.js]] — usa `KhipuRisk`
- [[engine.temporal-graph.js]] — usa `__tkgOpenObj`, `initTKGTab`
- [[engine.toast.js]] — usa `KhipuToast`
- [[engine.voice.js]] — usa `BixbyVoice`, `_executeTradeOrder`, `_openBrokerStage`, `_resolveTradeSymbol`, `_tradeAccountInfo`
- [[engine.xray.js]] — usa `buildXRayHTML`, `wireXRay`, `xrayEnsureStyles`
- [[nodes.nodes_seed.js]] — usa `CAT_TO_SECTOR`, `NODES`, `NODE_META`, `SECTORS9`

Se carga en [[app.html]] en la posición **88 de 96** (línea 7963), después de [[engine.desktop.js]] y antes de [[engine.live.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 88)
- [[app.html]] — usa `BixbyCockpit`
- [[engine.brief.js]] — usa `BixbyCockpit`
- [[engine.command_center.js]] — usa `BixbyCockpit`, `_openBrokerConfirm`, `_parseTradeCommand`
- [[engine.crypto.js]] — usa `BixbyCockpit`
- [[engine.fincard.js]] — usa `BixbyCockpit`
- [[engine.khipu_chat.js]] — usa `BixbyCockpit`
- [[engine.localcharts.js]] — usa `BixbyCockpit`
- [[engine.oswindows.js]] — usa `BixbyCockpit`
- [[engine.resolve.js]] — usa `BixbyCockpit`
- [[engine.voice.js]] — usa `BixbyCockpit`, `_computePortfolioSummary`, `_openDeepResearch`, `_runAgentSim`
- [[engine.xray.js]] — usa `BixbyCockpit`

## Endpoints que llama

- `GET /api/deep/status` → [[server.py]] ([[API deep]])
- `GET /api/findossier/<ticker>` → [[server.py]] ([[API findossier]])
- `GET /api/matrix/<rel_type>` → [[matrix.api.py]] ([[API matrix]])
- `GET /api/scalp/price/<path:symbol>` → [[server.py]] ([[API scalp]])
- `GET /api/screener/growth` → [[server.py]] ([[API screener]])
- `GET /api/trade/history` → [[server.py]] ([[API trade]])
- `GET /api/trade/positions/detail` → [[server.py]] ([[API trade]])
- `GET /api/voice/tour/<lang>/<int:step>` → [[server.py]] ([[API voice]])
- `POST /api/canvas/generate` → [[server.py]] ([[API canvas]])
- `POST /api/deep/analyze` → [[server.py]] ([[API deep]])
- `POST /api/matrix/insights` → [[matrix.api.py]] ([[API matrix]])
- `POST /api/portfolio/advice` → [[server.py]] ([[API portfolio]])
- `POST /api/portfolio/comment` → [[server.py]] ([[API portfolio]])
- `POST /api/sim/agents` → [[server.py]] ([[API sim]])
- `POST /api/thesis/quick` → [[server.py]] ([[API thesis]])
- `POST /api/trade/close` → [[server.py]] ([[API trade]])

## Pruebas que lo cubren

- [[tests.test_cleanup_client.py]]
- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_cleanup_modules_theme_i18n.py]]
- [[tests.test_committee_os_ui.py]]
- [[tests.test_khipu_chat.py]]
- [[tests.test_khipus_os_fixes_shell.py]]
- [[tests.test_khipus_os_integration.py]]
- [[tests.test_khipus_os_shell.py]]
- [[tests.test_live_labels_misc.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_overnight2_fixer_review.py]]
- [[tests.test_overnight2_scenes_tokens.py]]
- [[tests.test_overnight3_mic_voice_state.py]]
- [[tests.test_overnight3_toast_tokens.py]]
- [[tests.test_overnight_ui_dossier_clients.py]]
- [[tests.test_overnight_ui_small_panels.py]]
- [[tests.test_overnight_ui_xray_research.py]]
- [[tests.test_voice_os_client.py]]
- [[tests.test_voice_os_server.py]]
- [[tests.test_voice_tour.py]]
- [[tests.test_voice_tour_client.py]]
- [[tests.test_voice_tour_drive.py]]
- [[tests.test_voice_tour_narrator.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 (c) — LA VOZ DE KHIPU PARA KHIPUS OS + RECORRIDO DE UN MINUTO CON SU]]
- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-10-09 — EL COMITÉ ENTRA A KHIPUS OS (sw v250)]]
- [[Sesión 2026-10-06 (ii) — KHIPUS OS v1 (sw v245)]]
- [[Sesión 2026-10-04 (e) — INICIO DE LA CABINA REDISEÑADO + FEED SIN NOTICIAS VIEJAS]]
- [[Sesión 2026-10-04 (b) — ESCRITORIO - REVISIÓN ADVERSARIAL Y CORRECCIONES (sw v187)]]
- [[Sesión 2026-10-04 — ESCRITORIO KHIPU K1 - VENTANAS DENTRO DE LA CABINA (sw v186)]]
- [[Sesión 2026-10-03 — GASTO DE IA, SIM. ESTRUCTURAL, AVATARES, CANVAS, COMITÉ DE CARTERA]]
- [[Sesión 2026-09-28 (c) — DOSSIER PARA TODAS LAS EMPRESAS + DATOS EN VIVO (sw v151)]]
- [[Sesión 2026-09-28 — X-Ray pulido (sw v139)]]
- [[Sesión 2026-07 — Ampliaciones (tras feedback simulaciones muy cerradas, más info)]]
- [[Sesión 2026-10-03 — VISIÓN PRÓXIMA ETAPA (pedido, NO es parte de Phase 3)]]
