---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "engine/geosituation.js"
lenguaje: "javascript"
lineas: 14
aliases: ["engine/geosituation.js"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# engine/geosituation.js

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 14 líneas · `engine/geosituation.js`

## Para qué sirve

(RETIRADO 2026-09-30) Sala de Situación 2D. El mapa 2D de eventos ("muy grande y da poca info", feedback de Fabrizio) se FUSIONÓ en el World Monitor 3D (engine/worldmonitor.js): chokepoints con score vivo + "Simular cierre" (POST /api/matrix/impact), inestabilidad por país, fabs críticas, arcos de suministro y empresas viven ahora en el globo, con eventos en vivo encima. Este archivo queda como alias fino para que ningún llamador viejo (ni la caché del service worker) rompa: NO recrear el mapa 2D.

## API pública (globales que define)

`window.GeoSituation`

## Depende de

- [[engine.worldmonitor.js]] — usa `KhipuWorld`

Se carga en [[app.html]] en la posición **38 de 93** (línea 7811), después de [[engine.globe.js]] y antes de [[engine.canvas-data.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 38)

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-08-01 — Prompt frontend+IA (Cowork) - Tracks C y D implementados]]
