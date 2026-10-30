---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "engine/statematrix.js"
lenguaje: "javascript"
lineas: 76
aliases: ["engine/statematrix.js"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# engine/statematrix.js

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 76 líneas · `engine/statematrix.js`

## Para qué sirve

ESTADO VISUAL de la simulación (solo animación; SIN matemática de contagio) Paso 13 de INFRA_OPERATIVA (2026-10-13): el navegador ya NO propaga choques. Aquí había un segundo motor (máximo por "eslabón más débil", 8 iteraciones, sin umbral ni tope de fragilidad) que daba otros números que el servidor para la misma caída (PROP-01/02/12, G5-03). Ahora TODA cifra de impacto la da el kernel único del servidor por /api/hot/\* (engine/hotclient.js, window.KhipuHot). Este archivo solo convierte ese resultado en ESTADO VISUAL: · frames(res) la "película" de la cascada por SALTO (el `hop` que manda el servidor), para animar el mapa · baseline(id) signos vitales de presentación …

## API pública (globales que define)

`window.KhipuState`

## Depende de

- [[engine.app_main.js]] — usa `MKT`, `NODE_BY_ID`, `computeNRS`, `quotePx`
- [[engine.geo_coords.js]] — usa `GeoCoords`
- [[nodes.nodes_seed.js]] — usa `CAT_TO_SECTOR`, `NODES`

Se carga en [[app.html]] en la posición **71 de 104** (línea 3223), después de [[engine.insights.js]] y antes de [[engine.livesim.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 71)
- [[engine.compare.js]] — usa `KhipuState`
- [[engine.livesim.js]] — usa `KhipuState`

## Pruebas que lo cubren

- [[tests.test_countries.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_scenario_pnl_browser.py]]
- [[tests.test_voice_os_client.py]]
- [[tests.test_voice_tour_client.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (gg) — DIRECCIONES AL REVÉS + PESO DE LICENCIAS + PISO DEL KERNEL]]
- [[Sesión 2026-10-04 (h) — MISIÓN DE REPARACIÓN P0 INVESTIGACIÓN (R1-R6, sw v201)]]
