---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "engine/spacemonitor.js"
lenguaje: "javascript"
lineas: 1324
aliases: ["engine/spacemonitor.js"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# engine/spacemonitor.js

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 1.324 líneas · `engine/spacemonitor.js`

## Para qué sirve

SPACE MONITOR (pestaña 🚀 Espacio).

## API pública (globales que define)

`window.KhipuSpace`, `window._smGlobe`

## Depende de

- [[app.html]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `computeNRS`, `jumpTo`, `quotePx`, `switchTab`
- [[engine.explain.js]] — usa `explainChip`, `explainRegister`
- [[engine.geo_coords.js]] — usa `GeoCoords`
- [[engine.globe.js]] — usa `KhipuGlobe`
- [[engine.resolve.js]] — usa `_surface`
- [[engine.xray.js]] — usa `openXRay`
- [[nodes.nodes_seed.js]] — usa `NODES`, `NODE_META`, `sectorOf`

Se carga en [[app.html]] en la posición **55 de 95** (línea 7905), después de [[engine.worldmonitor.js]] y antes de [[engine.pickers.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 55)
- [[app.html]] — usa `KhipuSpace`

## Endpoints que llama

- `GET /api/space/tle` → [[server.py]] ([[API space]])
- `GET /api/space2/launches` → [[core.space.py]] ([[API space2]])
- `GET /api/space2/summary` → [[core.space.py]] ([[API space2]])

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
- [[Sesión 2026-09-30 al 10-02 — MONITORES, RIESGO FÁCIL, ASISTENTE, CEREBRO DE KHIPU]]
