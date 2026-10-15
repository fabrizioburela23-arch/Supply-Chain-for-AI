---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "engine/geo_coords.js"
lenguaje: "javascript"
lineas: 632
aliases: ["engine/geo_coords.js"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# engine/geo_coords.js

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 632 líneas · `engine/geo_coords.js`

## Para qué sirve

Coordenadas geográficas para los globos 3D (Khipu Finance) Los nodos NO traen lat/long: solo `country` (EEUU, Japon, "Estados Unidos (HQ Denver, CO)"…) y `loc`. Este módulo resuelve cada nodo a {lat,lng} de forma DETERMINISTA, y dice con qué PRECISIÓN lo hizo (regla del proyecto: no aparentar exactitud que no tenemos): 1) 'hq' → sede o sitio principal curado a mano (empresas clave), 2) 'city' → ciudad mencionada en el texto del país/loc ("Denver", "Pekín"), 3) 'hub' → EE.UU. sin ciudad: hub tecnológico asignado por hash (APROX.), 4) 'country' → centro económico del país + jitter determinista (APROX.), 5) 'unknown' → país no reconocido → hub global (Singapur). NO es su …

## API pública (globales que define)

`window.GeoCoords`, `window.KhipuCountries`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **41 de 101** (línea 3100), después de [[engine.secondbrain.js]] y antes de [[engine.globe.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 41)
- [[engine.catalog_sync.js]] — usa `KhipuCountries`
- [[engine.globe.js]] — usa `GeoCoords`
- [[engine.graph3d.js]] — usa `GeoCoords`, `KhipuCountries`
- [[engine.insights.js]] — usa `GeoCoords`
- [[engine.livesim.js]] — usa `GeoCoords`, `KhipuCountries`
- [[engine.spacemonitor.js]] — usa `GeoCoords`
- [[engine.statematrix.js]] — usa `GeoCoords`
- [[engine.temporal-graph.js]] — usa `GeoCoords`, `KhipuCountries`
- [[engine.universe2d.js]] — usa `GeoCoords`, `KhipuCountries`
- [[engine.worldmonitor.js]] — usa `GeoCoords`
- [[nodes.nodes_seed.js]] — usa `GeoCoords`, `KhipuCountries`

## Pruebas que lo cubren

- [[tests.test_countries.py]]
- [[tests.test_world.py]]
