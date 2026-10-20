---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "engine/globe.js"
lenguaje: "javascript"
lineas: 1037
aliases: ["engine/globe.js"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# engine/globe.js

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 1.037 líneas · `engine/globe.js`

## Para qué sirve

MOTOR GLOBO UNIFICADO (Track A, Fase 1 del prompt 2026-08). Fusión de engine/geoglobe.js + engine/planetarium.js: el boilerplate Three.js (escena/cámara/luces/starfield/drag/zoom táctil/resize/animate/Tierra con texturas /vendor) estaba duplicado casi línea a línea en dos WebGL contexts. Ahora se escribe UNA vez; las diferencias son CAPAS: 'companies' (empresas por NRS + arcos + chokepoints + etiquetas) y 'satellites' (constelaciones SGP4 en vivo). (Los alias window.KhipuGeoGlobe / window.Planetarium se borraron en el lote I4: nadie los usaba.) Los dos archivos originales se borraron en Track A Fase 2: este es el único motor.

## API pública (globales que define)

`window.KhipuGlobe`

## Depende de

- [[engine.app_main.js]] — usa `BASE`, `LINKS`, `computeNRS`
- [[engine.geo_coords.js]] — usa `GeoCoords`
- [[nodes.nodes_seed.js]] — usa `NODES`

Se carga en [[app.html]] en la posición **43 de 102** (línea 3102), después de [[engine.geo_coords.js]] y antes de [[engine.canvas-data.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 43)
- [[engine.spacemonitor.js]] — usa `KhipuGlobe`
- [[engine.worldmonitor.js]] — usa `KhipuGlobe`

## Pruebas que lo cubren

- [[tests.test_cleanup_modules_theme_i18n.py]]
- [[tests.test_space_satellites.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
- [[Sesión 2026-09-21 — Limpieza estructural - Track A Fase 2 + Track B completos]]
- [[Sesión 2026-08-01 — Prompt frontend+IA (Cowork) - Tracks C y D implementados]]
