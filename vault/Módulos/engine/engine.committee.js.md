---
tipo: "modulo"
capa: "Comité"
ruta: "engine/committee.js"
lenguaje: "javascript"
lineas: 1239
aliases: ["engine/committee.js"]
tags: ["capa/comite", "tipo/modulo"]
---

# engine/committee.js

> Módulo · capa [[Capa Comité]] · 1.239 líneas · `engine/committee.js`

## Para qué sirve

PHASE 3 · COMITÉ DE INVERSIÓN (con aprobación humana)

## API pública (globales que define)

`window.KhipuCommittee`

## Depende de

- [[app.html]] — usa `_tradeFetch`, `_tradePinStored`, `safeUrl`
- [[engine.app_main.js]] — usa `BASE`, `LANG`, `NODE_BY_ID`
- [[engine.clients.js]] — usa `KhipuClients`
- [[engine.explain.js]] — usa `explainChip`, `explainRegister`
- [[engine.mascot.js]] — usa `KhipuMascot`
- [[engine.pfcommittee.js]] — usa `KhipuPortfolioCommittee`
- [[engine.pickers.js]] — usa `KhipuPick`
- [[engine.research.js]] — usa `KhipuResearch`
- [[engine.toast.js]] — usa `KhipuToast`, `khipuActor`

Se carga en [[app.html]] en la posición **62 de 103** (línea 3199), después de [[engine.pickers.js]] y antes de [[engine.aispend.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 62)
- [[app.html]] — usa `KhipuCommittee`
- [[engine.brief.js]] — usa `KhipuCommittee`
- [[engine.cockpit.js]] — usa `KhipuCommittee`
- [[engine.genui.js]] — usa `KhipuCommittee`
- [[engine.khipu_chat.js]] — usa `KhipuCommittee`
- [[engine.khipu_lang.js]] — usa `KhipuCommittee`
- [[engine.oswindows.js]] — usa `KhipuCommittee`
- [[engine.pfcommittee.js]] — usa `KhipuCommittee`
- [[engine.pfreports.js]] — usa `KhipuCommittee`
- [[engine.research.js]] — usa `KhipuCommittee`
- [[engine.voice.js]] — usa `KhipuCommittee`
- [[engine.xray.js]] — usa `KhipuCommittee`

## Endpoints que llama

- `GET /api/committee/board` → [[research.committee_api.py]] ([[API committee]])
- `GET /api/committee/clients` → [[research.committee_api.py]] ([[API committee]])
- `GET /api/committee/entity/<entity_id>` → [[research.committee_api.py]] ([[API committee]])
- `GET /api/committee/memo/<memo_id>` → [[research.committee_api.py]] ([[API committee]])
- `GET /api/committee/outcomes/recent` → [[research.committee_api.py]] ([[API committee]])
- `GET /api/committee/track-record` → [[research.committee_api.py]] ([[API committee]])
- `GET /api/research/jobs/<job_id>` → [[research.api.py]] ([[API research]])
- `POST /api/committee/board/refresh` → [[research.committee_api.py]] ([[API committee]])
- `POST /api/committee/memo/<memo_id>/approve` → [[research.committee_api.py]] ([[API committee]])
- `POST /api/committee/memo/<memo_id>/reject` → [[research.committee_api.py]] ([[API committee]])
- `POST /api/committee/outcomes/evaluate` → [[research.committee_api.py]] ([[API committee]])
- `POST /api/committee/run` → [[research.committee_api.py]] ([[API committee]])
- `POST /api/research/jobs` → [[research.api.py]] ([[API research]])

## Pruebas que lo cubren

- [[tests.test_agents_registry.py]]
- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_committee_os_ui.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 (b) — LIMPIEZA QUE NO QUEDEN COSAS SUELTAS (sw v254)]]
- [[Sesión 2026-10-09 — EL COMITÉ ENTRA A KHIPUS OS (sw v250)]]
- [[Sesión 2026-10-03 (f) — PANEL DE TRADING BILINGÜE Y MÓVIL + APROBACIÓN DEL COMITÉ CON]]
- [[Sesión 2026-10-03 — GASTO DE IA, SIM. ESTRUCTURAL, AVATARES, CANVAS, COMITÉ DE CARTERA]]
- [[Sesión 2026-10-02 — SALA DEL COMITÉ - PUESTOS + DEBATE EN VIVO (sw v175)]]
- [[Sesión 2026-09-30 — PHASE 3 + WORLD MONITOR + CORRETAJE + MCP + ENDURECIMIENTO (sw v170)]]
