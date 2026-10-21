---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/oswindows.js"
lenguaje: "javascript"
lineas: 1646
aliases: ["engine/oswindows.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/oswindows.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 1.646 líneas · `engine/oswindows.js`

## Para qué sirve

VENTANAS NATIVAS de Khipus OS (2026-10-06)

## API pública (globales que define)

`window.KhipuOSWin`

## Depende de

- [[engine.app_main.js]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `_canonId`, `loadLiveQuotes`, `quoteAge`, `quoteAgoText`, `quotePx` y 2 más
- [[engine.cockpit.js]] — usa `BixbyCockpit`
- [[engine.committee.js]] — usa `KhipuCommittee`
- [[engine.explain.js]] — usa `explainMetric`, `explainRegister`
- [[engine.mascot.js]] — usa `KhipuAgentPrefs`, `KhipuMascot`
- [[engine.research.js]] — usa `KhipuResearch`
- [[engine.resolve.js]] — usa `KhipuResolve`
- [[engine.xray.js]] — usa `openXRay`
- [[nodes.nodes_seed.js]] — usa `NODES`

Se carga en [[app.html]] en la posición **91 de 103** (línea 3218), después de [[engine.genui.js]] y antes de [[engine.khipu_chat.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 91)
- [[engine.cockpit.js]] — usa `KhipuOSWin`
- [[engine.genui.js]] — usa `KhipuOSWin`
- [[engine.khipu_chat.js]] — usa `KhipuOSWin`
- [[engine.voice.js]] — usa `KhipuOSWin`

## Endpoints que llama

- `GET /api/agents/profiles` → [[core.agents_api.py]] ([[API agents]])
- `GET /api/committee/board` → [[research.committee_api.py]] ([[API committee]])
- `GET /api/committee/entity/<entity_id>` → [[research.committee_api.py]] ([[API committee]])
- `GET /api/committee/memo/<memo_id>` → [[research.committee_api.py]] ([[API committee]])
- `GET /api/tensor/node/<path:nid>` → [[matrix.tensor_api.py]] ([[API tensor]])
- `POST /api/committee/memo/<memo_id>/approve` → [[research.committee_api.py]] ([[API committee]])
- `POST /api/committee/memo/<memo_id>/reject` → [[research.committee_api.py]] ([[API committee]])

**Rutas que nombra y no existen en el servidor** (¿restos viejos?): `/api/hot/quote`

## Pruebas que lo cubren

- [[tests.test_ask_agent.py]]
- [[tests.test_genui_browser.py]]
- [[tests.test_genui_client_static.py]]
- [[tests.test_genui_k_browser.py]]
- [[tests.test_khipus_os_fixes_windows.py]]
- [[tests.test_khipus_os_integration.py]]
- [[tests.test_khipus_os_shell.py]]
- [[tests.test_khipus_os_windows.py]]
- [[tests.test_lotek_fixer.py]]
- [[tests.test_voice_tour_client.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (iii) — HABILIDADES PROPIAS DE CADA AGENTE (sw v247)]]
- [[Sesión 2026-10-06 (ii) — KHIPUS OS v1 (sw v245)]]
