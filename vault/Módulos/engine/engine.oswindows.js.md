---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/oswindows.js"
lenguaje: "javascript"
lineas: 1506
aliases: ["engine/oswindows.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/oswindows.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 1.506 líneas · `engine/oswindows.js`

## Para qué sirve

VENTANAS NATIVAS de Khipus OS (2026-10-06)

## API pública (globales que define)

`window.KhipuOSWin`, `window.KhipuOSWin_memoLine`

## Depende de

- [[app.html]] — usa `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `_canonId`, `loadLiveQuotes`, `quoteAge`, `quoteAgoText`, `quotePx`, `quoteSrcChip` y 1 más
- [[engine.cockpit.js]] — usa `BixbyCockpit`
- [[engine.committee.js]] — usa `KhipuCommittee`
- [[engine.explain.js]] — usa `explainMetric`, `explainRegister`
- [[engine.mascot.js]] — usa `KhipuAgentPrefs`, `KhipuMascot`
- [[engine.research.js]] — usa `KhipuResearch`
- [[engine.resolve.js]] — usa `KhipuResolve`
- [[engine.xray.js]] — usa `openXRay`
- [[nodes.nodes_seed.js]] — usa `NODES`

Se carga en [[app.html]] en la posición **81 de 92** (línea 7931), después de [[engine.portfolios.js]] y antes de [[engine.khipu_chat.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 81)
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

## Pruebas que lo cubren

- [[tests.test_ask_agent.py]]
- [[tests.test_khipus_os_fixes_windows.py]]
- [[tests.test_khipus_os_integration.py]]
- [[tests.test_khipus_os_shell.py]]
- [[tests.test_khipus_os_windows.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (iii) — HABILIDADES PROPIAS DE CADA AGENTE (sw v247)]]
- [[Sesión 2026-10-06 (ii) — KHIPUS OS v1 (sw v245)]]
