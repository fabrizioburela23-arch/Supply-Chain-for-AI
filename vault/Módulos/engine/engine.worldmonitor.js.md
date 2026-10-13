---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "engine/worldmonitor.js"
lenguaje: "javascript"
lineas: 1326
aliases: ["engine/worldmonitor.js"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# engine/worldmonitor.js

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 1.326 líneas · `engine/worldmonitor.js`

## Para qué sirve

WORLD MONITOR geopolítico (pestaña 🌐 Geopolítica).

## API pública (globales que define)

`window.KhipuWorld`, `window._wmGlobe`

## Depende de

- [[app.html]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `computeNRS`, `goMap`, `nexusCore`, `switchTab`
- [[engine.explain.js]] — usa `explainChip`, `explainRegister`
- [[engine.geo_coords.js]] — usa `GeoCoords`
- [[engine.globe.js]] — usa `KhipuGlobe`
- [[engine.resolve.js]] — usa `_surface`
- [[engine.xray.js]] — usa `openXRay`
- [[nodes.nodes_seed.js]] — usa `NODES`

Se carga en [[app.html]] en la posición **54 de 95** (línea 7906), después de [[engine.riskreport.js]] y antes de [[engine.spacemonitor.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 54)
- [[app.html]] — usa `KhipuWorld`
- [[engine.khipu_chat.js]] — usa `KhipuWorld`

## Endpoints que llama

- `GET /api/matrix/<rel_type>` → [[matrix.api.py]] ([[API matrix]])
- `GET /api/matrix/status` → [[matrix.api.py]] ([[API matrix]])
- `GET /api/world/brief` → [[core.world.py]] ([[API world]])
- `GET /api/world/events` → [[core.world.py]] ([[API world]])
- `GET /api/world/exposure` → [[core.world.py]] ([[API world]])
- `GET /api/world/gpr` → [[core.world.py]] ([[API world]])
- `GET /api/world/policy` → [[core.world.py]] ([[API world]])
- `GET /api/world/reference` → [[core.world.py]] ([[API world]])
- `POST /api/matrix/impact` → [[matrix.api.py]] ([[API matrix]])
- `POST /api/quotes/live` → [[server.py]] ([[API quotes]])

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
- [[Sesión 2026-10-05 (n) — GEOPOLÍTICA CON FUENTES OFICIALES (sw v216)]]
- [[Sesión 2026-09-30 — PHASE 3 + WORLD MONITOR + CORRETAJE + MCP + ENDURECIMIENTO (sw v170)]]
