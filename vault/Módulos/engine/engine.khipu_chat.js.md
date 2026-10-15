---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "engine/khipu_chat.js"
lenguaje: "javascript"
lineas: 1452
aliases: ["engine/khipu_chat.js"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# engine/khipu_chat.js

> Módulo · capa [[Capa Chat y agentes]] · 1.452 líneas · `engine/khipu_chat.js`

## Para qué sirve

EL CHAT de Khipu (texto), compartido por la Cabina (engine/cockpit.js) y el Command Center (engine/command_center.js).

## API pública (globales que define)

`window.KhipuChat`

## Depende de

- [[app.html]] — usa `safeUrl`
- [[engine.app_coordinator.js]] — usa `nexusCore`
- [[engine.app_main.js]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `_liveSelectedNode`, `_selectedNode`, `activeTab`, `jumpTo`, `switchTab`
- [[engine.cockpit.js]] — usa `BixbyCockpit`
- [[engine.committee.js]] — usa `KhipuCommittee`
- [[engine.desktop.js]] — usa `KhipuDesk`
- [[engine.fincard.js]] — usa `openFinCard`
- [[engine.genui.js]] — usa `KhipuGenUI`
- [[engine.genui_progress.js]] — usa `KhipuGenUIProgress`
- [[engine.mascot.js]] — usa `KhipuAgentPrefs`, `KhipuMascot`
- [[engine.oswindows.js]] — usa `KhipuOSWin`
- [[engine.pfcommittee.js]] — usa `KhipuPortfolioCommittee`, `KhipuProfile`
- [[engine.portfolios.js]] — usa `KhipuPortfolios`
- [[engine.research.js]] — usa `KhipuResearch`
- [[engine.resolve.js]] — usa `KhipuResolve`, `_surface`
- [[engine.riskreport.js]] — usa `KhipuRisk`
- [[engine.toast.js]] — usa `khipuActor`
- [[engine.worldmonitor.js]] — usa `KhipuWorld`
- [[engine.xray.js]] — usa `openXRay`
- [[nodes.legal_names.js]] — usa `LEGAL_NAMES`

Se carga en [[app.html]] en la posición **90 de 100** (línea 3215), después de [[engine.oswindows.js]] y antes de [[engine.desktop.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 90)
- [[engine.cockpit.js]] — usa `KhipuChat`
- [[engine.command_center.js]] — usa `KhipuChat`
- [[engine.genui.js]] — usa `KhipuChat`
- [[engine.genui_progress.js]] — usa `KhipuChat`
- [[engine.pickers.js]] — usa `KhipuChat`
- [[engine.voice.js]] — usa `KhipuChat`

## Endpoints que llama

- `GET /api/khipu/chat/progress/<req_id>` → [[core.khipu_chat.py]] ([[API khipu]])
- `POST /api/committee/portfolio/ask` → [[research.committee_api.py]] ([[API committee]])
- `POST /api/khipu/chat` → [[core.khipu_chat.py]] ([[API khipu]])

## Pruebas que lo cubren

- [[tests.test_agents_registry.py]]
- [[tests.test_chat_commands.py]]
- [[tests.test_chat_portfolio_agent.py]]
- [[tests.test_chat_portfolio_source_news.py]]
- [[tests.test_cleanup_client.py]]
- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_committee_os_ui.py]]
- [[tests.test_genui_browser.py]]
- [[tests.test_genui_client_static.py]]
- [[tests.test_genui_f3_client_static.py]]
- [[tests.test_khipu_chat.py]]
- [[tests.test_khipus_os_chat.py]]
- [[tests.test_lotej_review_fixes.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_voice_os_client.py]]
- [[tests.test_voice_tour_client.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 (b) — LIMPIEZA QUE NO QUEDEN COSAS SUELTAS (sw v254)]]
- [[Sesión 2026-10-06 (ii) — KHIPUS OS v1 (sw v245)]]
- [[Sesión 2026-10-05 (j) — COMANDOS Y AGENTES EN EL CHAT (sw v212)]]
- [[Sesión 2026-10-04 (g) — KHIPU COMO ASISTENTE - ANALISTAS EN EL CHAT, PROMPT, MEMORIA]]
- [[Sesión 2026-09-30 al 10-02 — MONITORES, RIESGO FÁCIL, ASISTENTE, CEREBRO DE KHIPU]]
