---
tipo: "modulo"
capa: "Voz"
ruta: "engine/voice.js"
lenguaje: "javascript"
lineas: 2116
aliases: ["engine/voice.js"]
tags: ["capa/voz", "tipo/modulo"]
---

# engine/voice.js

> Módulo · capa [[Capa Voz]] · 2.116 líneas · `engine/voice.js`

## Para qué sirve

Khipu, el asistente de voz de Khipu Finance Cliente WebSocket de ElevenLabs Agents (Conversational AI). Khipu es el "Jarvis de las finanzas": escucha por micrófono, responde por voz, y puede controlar la terminal.

## API pública (globales que define)

`window.BixbyVoice`, `window.KhipuVoiceAudio`, `window.__bixbyEnergy`, `window.__lastTradeExec`, `window.__tradeAcctCache`, `window.__tradeInflight`, `window._executeTradeOrder`, `window._openBrokerStage`, `window._resolveTradeSymbol`, `window._tradeAccountInfo`

De nivel superior (globales del script): `VOICE_TOOL_TIMEOUT_DEFAULT_S`, `VOICE_TOOL_TIMEOUT_S`, `VoiceAudio`, `_voiceL`, `_voiceLang`, `_voicePx`

## Depende de

- [[app.html]] — usa `BASE`, `LANG`, `LINKS`, `NODE_BY_ID`, `_liveRecolorByImpact`, `_openSecondBrain`, `_termOpenTicker`, `_tradeErrText`, `_tradeFetch`, `_tradeOrderAmbiguous` y 15 más
- [[engine.cockpit.js]] — usa `BixbyCockpit`, `_computePortfolioSummary`, `_openDeepResearch`, `_runAgentSim`
- [[engine.compare.js]] — usa `openCompare`
- [[engine.fincard.js]] — usa `openFinCard`
- [[engine.khipu_chat.js]] — usa `KhipuChat`
- [[engine.orb.js]] — usa `BixbyOrb`
- [[engine.resolve.js]] — usa `KhipuResolve`, `_surface`
- [[engine.statematrix.js]] — usa `KhipuState`
- [[engine.toast.js]] — usa `KhipuToast`
- [[engine.xray.js]] — usa `openXRay`
- [[nodes.nodes_seed.js]] — usa `CATS`, `NODES`, `NODE_META`
- [[sim.scenario_builder.js]] — usa `ScenarioBuilder`

Se carga en [[app.html]] en la posición **34 de 93** (línea 7807), después de [[engine.orb.js]] y antes de [[engine.secondbrain.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 34)
- [[app.html]] — usa `BixbyVoice`
- [[engine.cockpit.js]] — usa `BixbyVoice`, `_executeTradeOrder`, `_openBrokerStage`, `_resolveTradeSymbol`, `_tradeAccountInfo`
- [[engine.command_center.js]] — usa `BixbyVoice`
- [[engine.fincard.js]] — usa `BixbyVoice`
- [[engine.resolve.js]] — usa `_openBrokerStage`

## Endpoints que llama

- `GET /api/matrix/<rel_type>` → [[matrix.api.py]] ([[API matrix]])
- `GET /api/news/<ticker>` → [[server.py]] ([[API news]])
- `GET /api/space/launches` → [[server.py]] ([[API space]])
- `GET /api/space/tle` → [[server.py]] ([[API space]])
- `GET /api/trade/account` → [[server.py]] ([[API trade]])
- `GET /api/trade/crypto/assets` → [[server.py]] ([[API trade]])
- `GET /api/trade/positions/detail` → [[server.py]] ([[API trade]])
- `GET /api/voice/bixby-prompt` → [[server.py]] ([[API voice]])
- `POST /api/matrix/insights` → [[matrix.api.py]] ([[API matrix]])
- `POST /api/news/portfolio` → [[core.portfolio_reports_api.py]] ([[API news]])
- `POST /api/trade/order` → [[server.py]] ([[API trade]])
- `POST /api/voice/session` → [[server.py]] ([[API voice]])

## Pruebas que lo cubren

- [[tests.test_client_hardening.py]]
- [[tests.test_overnight3_fixer_voice_race.py]]
- [[tests.test_overnight3_mic_voice_state.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_overnight_voice_client.py]]
- [[tests.test_overnight_voice_server.py]]
- [[tests.test_server_smoke.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-07-14 — (madrugada, autónoma) — víspera de la demo app en v95]]
- [[Sesión 2026-07-05 — Etapa 1 — Limpieza masiva - COMPLETA (4 batches publicados)]]
- [[Sesión 2026-07 — Ampliaciones (tras feedback simulaciones muy cerradas, más info)]]
- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
- [[Sesión 2026-07-13 — Etapa M — Trading cripto en papel, integrado en Khipu (sw v80)]]
