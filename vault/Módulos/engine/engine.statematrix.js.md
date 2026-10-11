---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "engine/statematrix.js"
lenguaje: "javascript"
lineas: 234
aliases: ["engine/statematrix.js"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# engine/statematrix.js

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 234 líneas · `engine/statematrix.js`

## Para qué sirve

MOTOR DE ESTADOS REACTIVO (client-side, 60 fps) El "sistema nervioso" de Khipus: cada empresa tiene un VECTOR DE ESTADO (signos vitales); las MATRICES DE ACOPLAMIENTO (una por tipo de relación) son su entorno; un KERNEL reactivo re-adapta los valores cuando algo cambia.

## API pública (globales que define)

`window.KhipuState`

## Depende de

- [[app.html]] — usa `LINKS`, `MKT`, `computeNRS`
- [[nodes.nodes_seed.js]] — usa `CAT_TO_SECTOR`, `NODES`

Se carga en [[app.html]] en la posición **66 de 93** (línea 7905), después de [[engine.insights.js]] y antes de [[engine.livesim.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 66)
- [[app.html]] — usa `KhipuState`
- [[engine.cockpit.js]] — usa `KhipuState`
- [[engine.compare.js]] — usa `KhipuState`
- [[engine.livesim.js]] — usa `KhipuState`
- [[engine.voice.js]] — usa `KhipuState`
- [[engine.xray.js]] — usa `KhipuState`

## Pruebas que lo cubren

- [[tests.test_repair_graph.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (gg) — DIRECCIONES AL REVÉS + PESO DE LICENCIAS + PISO DEL KERNEL]]
- [[Sesión 2026-10-04 (h) — MISIÓN DE REPARACIÓN P0 INVESTIGACIÓN (R1-R6, sw v201)]]
