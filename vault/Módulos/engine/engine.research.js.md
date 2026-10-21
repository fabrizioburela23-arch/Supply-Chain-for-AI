---
tipo: "modulo"
capa: "Investigación"
ruta: "engine/research.js"
lenguaje: "javascript"
lineas: 591
aliases: ["engine/research.js"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# engine/research.js

> Módulo · capa [[Capa Investigación]] · 591 líneas · `engine/research.js`

## Para qué sirve

PHASE 2 · INVESTIGACIÓN IA (Agent Research Swarm)

## API pública (globales que define)

`window.KhipuResearch`

## Depende de

- [[engine.app_main.js]] — usa `BASE`, `LANG`, `NODE_BY_ID`, `jumpTo`
- [[engine.committee.js]] — usa `KhipuCommittee`
- [[engine.explain.js]] — usa `explainChip`
- [[engine.mascot.js]] — usa `KhipuMascot`
- [[engine.toast.js]] — usa `KhipuToast`, `khipuActor`

Se carga en [[app.html]] en la posición **56 de 103** (línea 3142), después de [[engine.xray.js]] y antes de [[engine.riskreport.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 56)
- [[engine.app_main.js]] — usa `KhipuResearch`
- [[engine.cockpit.js]] — usa `KhipuResearch`
- [[engine.committee.js]] — usa `KhipuResearch`
- [[engine.genui.js]] — usa `KhipuResearch`
- [[engine.khipu_chat.js]] — usa `KhipuResearch`
- [[engine.khipu_lang.js]] — usa `KhipuResearch`
- [[engine.oswindows.js]] — usa `KhipuResearch`
- [[engine.voice.js]] — usa `KhipuResearch`
- [[engine.xray.js]] — usa `KhipuResearch`

## Endpoints que llama

- `GET /api/committee/calibration` → [[research.committee_api.py]] ([[API committee]])
- `GET /api/committee/track-record` → [[research.committee_api.py]] ([[API committee]])
- `GET /api/research/activity` → [[research.api.py]] ([[API research]])
- `GET /api/research/claims/<claim_id>` → [[research.api.py]] ([[API research]])
- `GET /api/research/entity/<entity_id>` → [[research.api.py]] ([[API research]])
- `GET /api/research/jobs/<job_id>` → [[research.api.py]] ([[API research]])
- `POST /api/research/jobs` → [[research.api.py]] ([[API research]])

## Pruebas que lo cubren

- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_overnight_ui_xray_research.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-09-28 (e) — PHASE 2 - AGENT RESEARCH SWARM (sw v153)]]
