---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/genui.js"
lenguaje: "javascript"
lineas: 1435
aliases: ["engine/genui.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/genui.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 1.435 líneas · `engine/genui.js`

## Para qué sirve

RESPUESTAS VISUALES del chat (kblocks/1): docs/CHAT_UI_GENERATIVA.md §7. Dibuja; NUNCA calcula cifras. DOM seguro, 17 tipos, acciones solo abrir/sugerir, tokens --os-\*, bilingüe; charts/shapes PEREZOSOS.

## API pública (globales que define)

`window.KhipuGenUI`, `window.__kosKindQueue`

## Depende de

- [[app.html]] — usa `safeUrl`
- [[engine.app_main.js]] — usa `BASE`, `LANG`, `NODE_BY_ID`
- [[engine.cockpit.js]] — usa `BixbyCockpit`
- [[engine.committee.js]] — usa `KhipuCommittee`
- [[engine.explain.js]] — usa `explainMetric`, `explainRegister`
- [[engine.khipu_chat.js]] — usa `KhipuChat`
- [[engine.oswindows.js]] — usa `KhipuOSWin`
- [[engine.research.js]] — usa `KhipuResearch`
- [[engine.resolve.js]] — usa `_surface`
- [[engine.toast.js]] — usa `KhipuToast`
- [[engine.worldmonitor.js]] — usa `KhipuWorld`

Se carga en [[app.html]] en la posición **90 de 102** (línea 3217), después de [[engine.portfolios.js]] y antes de [[engine.oswindows.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 90)
- [[engine.cockpit.js]] — usa `KhipuGenUI`
- [[engine.genui_charts.js]] — usa `KhipuGenUI`
- [[engine.genui_progress.js]] — usa `KhipuGenUI`
- [[engine.genui_shapes.js]] — usa `KhipuGenUI`
- [[engine.khipu_chat.js]] — usa `KhipuGenUI`

## Endpoints que llama

- `GET /api/ledger/why/<decision_id>` → [[core.ledger_api.py]] ([[API ledger]])

**Rutas que nombra y no existen en el servidor** (¿restos viejos?): `/api/genui/block`

## Pruebas que lo cubren

- [[tests.test_genui_browser.py]]
- [[tests.test_genui_client_static.py]]
- [[tests.test_genui_f3_client_static.py]]
- [[tests.test_genui_render_node.py]]
- [[tests.test_genui_review_fixes.py]]
- [[tests.test_lotek_fixer.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-14 — RESPUESTAS VISUALES F2 - revisión (19 hallazgos) — sw v269]]
