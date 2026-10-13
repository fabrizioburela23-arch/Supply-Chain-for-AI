---
tipo: "modulo"
capa: "Voz"
ruta: "engine/voice.js"
lenguaje: "javascript"
lineas: 3078
aliases: ["engine/voice.js"]
tags: ["capa/voz", "tipo/modulo"]
---

# engine/voice.js

> Módulo · capa [[Capa Voz]] · 3.078 líneas · `engine/voice.js`

## Para qué sirve

Khipu, el asistente de voz de Khipu Finance Cliente WebSocket de ElevenLabs Agents (Conversational AI). Khipu es el "Jarvis de las finanzas": escucha por micrófono, responde por voz, y puede controlar la terminal.

## API pública (globales que define)

`window.BixbyVoice`, `window.KhipuVoiceAudio`, `window.__bixbyEnergy`, `window.__lastTradeExec`, `window.__tradeAcctCache`, `window.__tradeInflight`, `window._executeTradeOrder`, `window._openBrokerStage`, `window._resolveTradeSymbol`, `window._tradeAccountInfo`

De nivel superior (globales del script): `NARRATE_STALL_MS`, `NARRATE_START_MS`, `TOUR_AUDIO_GAP_MS`, `TOUR_DRIVE_GAP_MS`, `TOUR_SPEECH_CPS`, `TOUR_TAG_RE`, `VOICE_ALIAS_TIMEOUT_S`, `VOICE_ORDER_PREVIEW_MS`, `VOICE_TOOL_TIMEOUT_DEFAULT_S`, `VOICE_TOOL_TIMEOUT_S`, `VoiceAudio`, `_voiceL`, `_voiceLang`, `_voicePx`, `_voiceSimSev`

## Depende de

- [[app.html]] — usa `BASE`, `KhipuLive`, `LANG`, `LINKS`, `NODE_BY_ID`, `NRS_FLOW_TYPES`, `V8`, `_canonId`, `_liveRecolorByImpact`, `_liveSelectedNode` y 20 más
- [[engine.cockpit.js]] — usa `BixbyCockpit`, `_computePortfolioSummary`, `_openDeepResearch`, `_runAgentSim`
- [[engine.committee.js]] — usa `KhipuCommittee`
- [[engine.compare.js]] — usa `openCompare`
- [[engine.desktop.js]] — usa `KhipuDesk`
- [[engine.fincard.js]] — usa `openFinCard`
- [[engine.khipu_chat.js]] — usa `KhipuChat`
- [[engine.live.js]] — usa `KhipuLive`
- [[engine.mascot.js]] — usa `KhipuAgentPrefs`
- [[engine.orb.js]] — usa `BixbyOrb`
- [[engine.oswindows.js]] — usa `KhipuOSWin`
- [[engine.research.js]] — usa `KhipuResearch`
- [[engine.resolve.js]] — usa `KhipuResolve`, `_surface`
- [[engine.toast.js]] — usa `KhipuToast`
- [[engine.xray.js]] — usa `openXRay`
- [[nodes.legal_names.js]] — usa `LEGAL_NAMES`
- [[nodes.nodes_seed.js]] — usa `CAT_TO_SECTOR`, `NODES`, `NODE_META`, `SECTORS9`
- [[nodes.private_valuations.js]] — usa `PRIVATE_VALUATIONS`
- [[sim.scenario_builder.js]] — usa `ScenarioBuilder`

Se carga en [[app.html]] en la posición **35 de 96** (línea 7844), después de [[engine.orb.js]] y antes de [[engine.secondbrain.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 35)
- [[app.html]] — usa `BixbyVoice`
- [[engine.cockpit.js]] — usa `BixbyVoice`, `_executeTradeOrder`, `_openBrokerStage`, `_resolveTradeSymbol`, `_tradeAccountInfo`
- [[engine.command_center.js]] — usa `BixbyVoice`
- [[engine.fincard.js]] — usa `BixbyVoice`
- [[engine.resolve.js]] — usa `_openBrokerStage`

## Endpoints que llama

- `GET /api/matrix/<rel_type>` → [[matrix.api.py]] ([[API matrix]])
- `GET /api/space/launches` → [[server.py]] ([[API space]])
- `GET /api/space/tle` → [[server.py]] ([[API space]])
- `GET /api/trade/account` → [[server.py]] ([[API trade]])
- `GET /api/trade/crypto/assets` → [[server.py]] ([[API trade]])
- `GET /api/trade/positions/detail` → [[server.py]] ([[API trade]])
- `GET /api/voice/bixby-prompt` → [[server.py]] ([[API voice]])
- `POST /api/matrix/insights` → [[matrix.api.py]] ([[API matrix]])
- `POST /api/trade/order` → [[server.py]] ([[API trade]])
- `POST /api/voice/session` → [[server.py]] ([[API voice]])

## Pruebas que lo cubren

- [[tests.test_client_hardening.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_overnight3_fixer_voice_race.py]]
- [[tests.test_overnight3_mic_voice_state.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_overnight_voice_client.py]]
- [[tests.test_overnight_voice_server.py]]
- [[tests.test_review_infra_c.py]]
- [[tests.test_server_smoke.py]]
- [[tests.test_voice_os_client.py]]
- [[tests.test_voice_tour.py]]
- [[tests.test_voice_tour_client.py]]
- [[tests.test_voice_tour_drive.py]]
- [[tests.test_voice_tour_narrator.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-12 (b) — EL RECORRIDO DE VOZ YA NO SE QUEDA EN EL PASO 1 (sw v257)]]
- [[Sesión 2026-10-11 (c) — LA VOZ DE KHIPU PARA KHIPUS OS + RECORRIDO DE UN MINUTO CON SU]]
- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-07-14 — (madrugada, autónoma) — víspera de la demo app en v95]]
- [[Sesión 2026-07-05 — Etapa 1 — Limpieza masiva - COMPLETA (4 batches publicados)]]
- [[Sesión 2026-07 — Ampliaciones (tras feedback simulaciones muy cerradas, más info)]]
- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
- [[Sesión 2026-07-13 — Etapa M — Trading cripto en papel, integrado en Khipu (sw v80)]]
