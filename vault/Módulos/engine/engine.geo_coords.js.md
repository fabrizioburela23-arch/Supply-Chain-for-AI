---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "engine/geo_coords.js"
lenguaje: "javascript"
lineas: 396
aliases: ["engine/geo_coords.js"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# engine/geo_coords.js

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 396 líneas · `engine/geo_coords.js`

## Para qué sirve

Coordenadas geográficas para los globos 3D (Khipu Finance) Los nodos NO traen lat/long: solo `country` (EEUU, Japon, "Estados Unidos (HQ Denver, CO)"…) y `loc`. Este módulo resuelve cada nodo a {lat,lng} de forma DETERMINISTA, y dice con qué PRECISIÓN lo hizo (regla del proyecto: no aparentar exactitud que no tenemos): 1) 'hq' → sede o sitio principal curado a mano (empresas clave), 2) 'city' → ciudad mencionada en el texto del país/loc ("Denver", "Pekín"), 3) 'hub' → EE.UU. sin ciudad: hub tecnológico asignado por hash (APROX.), 4) 'country' → centro económico del país + jitter determinista (APROX.), 5) 'unknown' → país no reconocido → hub global (Singapur). NO es su …

## API pública (globales que define)

`window.GeoCoords`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **36 de 92** (línea 7820), después de [[engine.secondbrain.js]] y antes de [[engine.globe.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 36)
- [[engine.globe.js]] — usa `GeoCoords`
- [[engine.spacemonitor.js]] — usa `GeoCoords`
- [[engine.worldmonitor.js]] — usa `GeoCoords`

## Pruebas que lo cubren

- [[tests.test_world.py]]
