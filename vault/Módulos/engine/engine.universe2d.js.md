---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/universe2d.js"
lenguaje: "javascript"
lineas: 1059
aliases: ["engine/universe2d.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/universe2d.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 1.059 líneas · `engine/universe2d.js`

## Para qué sirve

Universo 2D: respaldo TOTAL del mapa 3D sin WebGL.

## API pública (globales que define)

`window.KhipuUniverse2D`

## Depende de

- [[engine.app_coordinator.js]] — usa `_diag`
- [[engine.app_main.js]] — usa `LANG`, `computeNRS`, `computeNodeRadius`, `getCatColorHex`, `jumpTo`
- [[engine.geo_coords.js]] — usa `GeoCoords`, `KhipuCountries`
- [[nodes.nodes_seed.js]] — usa `CATS`, `CAT_TO_SECTOR`, `SECTORS9`

Se carga en [[app.html]] en la posición **35 de 103** (línea 3121), después de [[engine.mascot.js]] y antes de [[engine.resolve.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 35)
- [[engine.app_coordinator.js]] — usa `KhipuUniverse2D`

## Pruebas que lo cubren

- [[tests.test_countries.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
- [[Sesión 2026-07-12 — Etapa K — Burbujas cripto + universo 2D + caso Opera (sw v77)]]
- [[Sesión 2026-07-12 — Etapa L — Universo 2D como motor PRINCIPAL (sw v78)]]
- [[Sesión 2026-07-13 — Etapa N — CAUSA RAÍZ del 3D no da ENCONTRADA Y CORREGIDA (sw v84)]]
