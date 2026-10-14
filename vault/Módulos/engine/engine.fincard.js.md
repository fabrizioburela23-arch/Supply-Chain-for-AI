---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "engine/fincard.js"
lenguaje: "javascript"
lineas: 1202
aliases: ["engine/fincard.js"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# engine/fincard.js

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 1.202 líneas · `engine/fincard.js`

## Para qué sirve

DOSSIER FINANCIERO de una empresa (Etapa G, 2026-07-11) Estilo investingvisuals que pidió Fabrizio: una tarjeta con small-multiples de indicadores reales — crecimiento de ingresos, dilución, free cash flow, acción, valuación EV/Ventas, deuda/capital, márgenes y ROE.

## API pública (globales que define)

`window._finCardClose`, `window._finCardCompare`, `window._finCardOpenParent`, `window.openFinCard`

## Depende de

- [[engine.app_coordinator.js]] — usa `_openDossier`
- [[engine.app_main.js]] — usa `BASE`, `LANG`, `NODE_BY_ID`
- [[engine.cockpit.js]] — usa `BixbyCockpit`
- [[engine.explain.js]] — usa `explainChip`
- [[engine.resolve.js]] — usa `KhipuResolve`
- [[engine.voice.js]] — usa `BixbyVoice`
- [[nodes.nodes_seed.js]] — usa `NODES`, `NODE_META`
- [[nodes.preipo_intel.js]] — usa `PREIPO_INTEL`
- [[nodes.private_valuations.js]] — usa `PRIVATE_VALUATIONS`

Se carga en [[app.html]] en la posición **76 de 99** (línea 3199), después de [[engine.localcharts.js]] y antes de [[engine.termdata.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 76)
- [[engine.app_coordinator.js]] — usa `openFinCard`
- [[engine.cockpit.js]] — usa `openFinCard`
- [[engine.khipu_chat.js]] — usa `openFinCard`
- [[engine.resolve.js]] — usa `openFinCard`
- [[engine.termdata.js]] — usa `openFinCard`
- [[engine.voice.js]] — usa `openFinCard`
- [[engine.xray.js]] — usa `openFinCard`

## Endpoints que llama

- `GET /api/candles/<ticker>` → [[server.py]] ([[API candles]])
- `GET /api/company/live/<ticker>` → [[server.py]] ([[API company]])
- `GET /api/company/valuation/<path:name>` → [[server.py]] ([[API company]])
- `GET /api/findossier/<ticker>` → [[server.py]] ([[API findossier]])
- `GET /api/news/<ticker>` → [[server.py]] ([[API news]])
- `GET /api/news/gdelt/<company_name>` → [[server.py]] ([[API news]])
- `GET /api/ontology/objects/<object_id>/history` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/objects/<object_id>/links` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/objects/<object_id>/news` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/objects/<object_id>/provenance` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/objects/<object_id>/timeline` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/objects/<object_id>` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/objects` → [[ontology.api.py]] ([[API ontology]])

## Pruebas que lo cubren

- [[tests.test_overnight_ui_dossier_clients.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-09-28 (c) — DOSSIER PARA TODAS LAS EMPRESAS + DATOS EN VIVO (sw v151)]]
- [[Sesión 2026-09-28 — X-Ray pulido (sw v139)]]
- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
