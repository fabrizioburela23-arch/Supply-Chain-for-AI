---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "engine/livesim.js"
lenguaje: "javascript"
lineas: 430
aliases: ["engine/livesim.js"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# engine/livesim.js

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 430 líneas · `engine/livesim.js`

## Para qué sirve

SIMULACIÓN EN VIVO v3 (abierta, no cerrada) Constructor de escenarios: eliges el TIPO de golpe (corte↓, demanda↑, precio, sanción) y el OBJETIVO (preset, sector entero, país entero, o las empresas que tú elijas). Los nodos y conexiones reaccionan: rojo=daño. Las cifras salen del motor ÚNICO del servidor (/api/hot/\* vía engine/hotclient.js, factores activos incluidos; paso 13 INFRA_OPERATIVA): las mismas que el X-Ray, la Cabina y la voz. Aquí solo queda el estado VISUAL (película por salto con window.KhipuState.frames). Stats en \$, rivales poco golpeados, desglose por sector, ▶ película de la cascada. Botón "◉ En vivo". El auge de demanda (hacia proveedores) todavía no lo …

## API pública (globales que define)

`window._lsRemove`, `window._lsReplay`, `window._lsToggle`

## Depende de

- [[app.html]] — usa `LANG`, `MKT`, `NODE_BY_ID`, `_liveRecolorByImpact`, `_liveResetColors`, `_liveSelectedNode`, `_liveTintLinks`, `jumpTo`, `sectorName`
- [[engine.statematrix.js]] — usa `KhipuState`
- [[engine.toast.js]] — usa `khipuActor`
- [[nodes.nodes_seed.js]] — usa `CAT_TO_SECTOR`, `NODES`, `NODE_META`, `SECTORS9`

Se carga en [[app.html]] en la posición **67 de 96** (línea 7942), después de [[engine.statematrix.js]] y antes de [[engine.layers.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 67)
- [[engine.command_center.js]] — usa `_lsToggle`

## Endpoints que llama

- `GET /api/matrix/<rel_type>` → [[matrix.api.py]] ([[API matrix]])
- `GET /api/matrix/simulations` → [[matrix.api.py]] ([[API matrix]])
- `POST /api/matrix/simulations` → [[matrix.api.py]] ([[API matrix]])

## Pruebas que lo cubren

- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_no_client_engine.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-28 — X-Ray pulido (sw v139)]]
- [[Sesión 2026-07 — Ampliaciones (tras feedback simulaciones muy cerradas, más info)]]
