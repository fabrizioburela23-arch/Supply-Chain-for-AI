---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "engine/livesim.js"
lenguaje: "javascript"
lineas: 405
aliases: ["engine/livesim.js"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# engine/livesim.js

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 405 líneas · `engine/livesim.js`

## Para qué sirve

SIMULACIÓN EN VIVO v3 (abierta, no cerrada) Constructor de escenarios: eliges el TIPO de golpe (corte↓, demanda↑, precio, sanción) y el OBJETIVO (preset, sector entero, país entero, o las empresas que tú elijas). Los nodos y conexiones reaccionan en tiempo real (~7ms → 60fps): rojo=daño, verde=auge. Stats en \$, ganadores, desglose por sector, ▶ película de la cascada. Piel NEXUS. Botón "◉ En vivo".

## API pública (globales que define)

`window._lsRemove`, `window._lsReplay`, `window._lsToggle`

## Depende de

- [[app.html]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `_liveRecolorByImpact`, `_liveResetColors`, `_liveSelectedNode`, `_liveTintLinks`, `esc`, `jumpTo` y 1 más
- [[engine.statematrix.js]] — usa `KhipuState`
- [[nodes.nodes_seed.js]] — usa `CAT_TO_SECTOR`, `NODES`, `NODE_META`, `SECTORS9`

Se carga en [[app.html]] en la posición **67 de 93** (línea 7906), después de [[engine.statematrix.js]] y antes de [[engine.layers.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 67)
- [[engine.command_center.js]] — usa `_lsToggle`

## Endpoints que llama

- `GET /api/matrix/<rel_type>` → [[matrix.api.py]] ([[API matrix]])
- `GET /api/matrix/factors` → [[matrix.api.py]] ([[API matrix]])
- `GET /api/matrix/simulations` → [[matrix.api.py]] ([[API matrix]])
- `POST /api/matrix/simulations` → [[matrix.api.py]] ([[API matrix]])

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-28 — X-Ray pulido (sw v139)]]
- [[Sesión 2026-07 — Ampliaciones (tras feedback simulaciones muy cerradas, más info)]]
