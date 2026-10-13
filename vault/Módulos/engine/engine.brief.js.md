---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "engine/brief.js"
lenguaje: "javascript"
lineas: 301
aliases: ["engine/brief.js"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# engine/brief.js

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 301 líneas · `engine/brief.js`

## Para qué sirve

BRIEF MATINAL (te recibe con la inteligencia del día) Al abrir la app (una vez al día, descartable), un overlay NEXUS resume: el mayor chokepoint, la empresa de mayor riesgo, factores externos activos y una oportunidad. Reutiliza el motor único del servidor y, opcional, una línea narrada por IA (gasto moderado). No molesta: 1×/día, fácil de cerrar, y un botón ❓ para reabrirlo. KHIPUS OS (2026-10-06): NO se abre solo encima de Khipus OS (la app arranca en el OS salvo "Vista clásica"); queda a pedido (window._briefOpen, paleta ⌘K). Así el arranque no gasta una llamada de IA que compite con la primera pregunta del usuario. El cuello de botella sale SOLO del motor único del …

## API pública (globales que define)

`window._briefAutoAllowed`, `window._briefClose`, `window._briefCommittee`, `window._briefJump`, `window._briefOpen`

## Depende de

- [[app.html]] — usa `LANG`, `MKT`, `NODE_BY_ID`, `computeNRS`, `jumpTo`, `switchTab`
- [[engine.cockpit.js]] — usa `BixbyCockpit`
- [[engine.committee.js]] — usa `KhipuCommittee`
- [[engine.mascot.js]] — usa `KhipuMascot`
- [[engine.resolve.js]] — usa `_surface`
- [[nodes.nodes_seed.js]] — usa `NODES`

Se carga en [[app.html]] en la posición **69 de 95** (línea 7936), después de [[engine.layers.js]] y antes de [[engine.compare.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 69)
- [[engine.cockpit.js]] — usa `_briefOpen`

## Endpoints que llama

- `GET /api/committee/board` → [[research.committee_api.py]] ([[API committee]])
- `POST /api/ai/analyze` → [[server.py]] ([[API ai]])

## Pruebas que lo cubren

- [[tests.test_khipus_os_fixes_perf.py]]
- [[tests.test_khipus_os_perf.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_overnight_ui_small_panels.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-10-06 (ii) — KHIPUS OS v1 (sw v245)]]
