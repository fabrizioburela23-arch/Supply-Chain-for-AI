---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "engine/compare.js"
lenguaje: "javascript"
lineas: 168
aliases: ["engine/compare.js"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# engine/compare.js

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 168 líneas · `engine/compare.js`

## Para qué sirve

COMPARAR DOS EMPRESAS lado a lado (decidir entre 2) Overlay NEXUS: elige dos empresas y ve enfrentadas su NRS (término a término), sector, país, margen, precio en vivo, grado de conexión, señal de compra/venta y dependencias. El ganador de cada fila se resalta. Se abre con window.openCompare(idA, idB) o el botón "⇄ Comparar" del X-Ray. KHIPUS OS (2026-10-11): \#cmp-ov vive FUERA de \#bcp-ov y lleva .kos-themed → tokens --os-\* de engine/cockpit.js (claro = body sin .dark, oscuro = body.dark); el valor tras la coma de cada var() es el respaldo (piel NEXUS vieja). Con el comparador abierto, un cambio de idioma lo re-pinta.

## API pública (globales que define)

`window._cmpClose`, `window.openCompare`

## Depende de

- [[app.html]] — usa `LANG`, `LINKS`, `NODE_BY_ID`, `computeNRS`, `computeNRSBreakdown`, `sectorName`
- [[engine.statematrix.js]] — usa `KhipuState`
- [[nodes.nodes_seed.js]] — usa `CAT_TO_SECTOR`, `NODES`, `NODE_META`, `SECTORS9`

Se carga en [[app.html]] en la posición **69 de 92** (línea 7921), después de [[engine.brief.js]] y antes de [[engine.matrixview.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 69)
- [[engine.command_center.js]] — usa `openCompare`
- [[engine.resolve.js]] — usa `openCompare`
- [[engine.voice.js]] — usa `openCompare`
- [[engine.xray.js]] — usa `openCompare`

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-28 (b) — Estado en bolsa VERIFICADO (sw v142-143)]]
- [[Sesión 2026-07 — Ampliaciones (tras feedback simulaciones muy cerradas, más info)]]
