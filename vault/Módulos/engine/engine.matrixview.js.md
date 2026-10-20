---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "engine/matrixview.js"
lenguaje: "javascript"
lineas: 207
aliases: ["engine/matrixview.js"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# engine/matrixview.js

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 207 líneas · `engine/matrixview.js`

## Para qué sirve

LAS 9 MATRICES dentro de la app (pestaña Análisis) Calcula en el navegador las 9 matrices de relación desde window.LINKS y las dibuja: small-multiples (patrón de dispersión de cada tipo) + un mapa de calor grande de las empresas más conectadas, con tooltip al pasar el cursor. Se rellena \#an-matrix cuando se abre Análisis (renderAnalysis). KHIPUS OS (2026-10-11): \#an-matrix y la burbuja \#mxv-tip llevan .kos-themed → tokens --os-\* de engine/cockpit.js (claro = body sin .dark, oscuro = body.dark; el valor tras la coma de cada var() es el respaldo, la piel NEXUS vieja). Los canvas no entienden var(): leen los tokens al dibujar y se re-dibujan al cambiar el tema. Los …

## API pública (globales que define)

`window.renderMatrixView`

## Depende de

- [[engine.app_main.js]] — usa `LANG`, `LINKS`, `NODE_BY_ID`, `sectorName`
- [[nodes.nodes_seed.js]] — usa `CAT_TO_SECTOR`, `NODES`, `SECTORS9`

Se carga en [[app.html]] en la posición **76 de 102** (línea 3201), después de [[engine.compare.js]] y antes de [[engine.nav4.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 76)
- [[engine.app_main.js]] — usa `renderMatrixView`

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-07 — Ampliaciones (tras feedback simulaciones muy cerradas, más info)]]
