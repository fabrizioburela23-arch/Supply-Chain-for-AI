---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/catalog_sync.js"
lenguaje: "javascript"
lineas: 440
aliases: ["engine/catalog_sync.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/catalog_sync.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 440 líneas · `engine/catalog_sync.js`

## Para qué sirve

EXPANSION_5K E3.1 (lote L, 2026-10-15): el catálogo del navegador se COMPLETA con lo que solo está en Postgres.

## API pública (globales que define)

`window.KhipuCatalogSync`, `window.renderDetail`

## Depende de

- [[engine.app_main.js]] — usa `KhipuLiveFund`, `LANG`, `LINKS`, `NODE_BY_ID`, `_canonId`, `_invalidateNRS`, `_lblOn`, `_liveTick`, `_mapLayers`, `_mapState` y 13 más
- [[engine.geo_coords.js]] — usa `KhipuCountries`
- [[nodes.legal_names.js]] — usa `LEGAL_NAMES`
- [[nodes.nodes_seed.js]] — usa `CATS`, `NODES`, `NODE_ID_ALIAS`, `NODE_META`

Se carga en [[app.html]] en la posición **21 de 102** (línea 1523), después de [[nodes.merge_graph.js]] y antes de [[engine.pfstore.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 21)

**Rutas que nombra y no existen en el servidor** (¿restos viejos?): `/api/hot/catalog`, `/api/hot/catalog/detail`

## Pruebas que lo cubren

- [[tests.test_catalog_api_client.py]]
- [[tests.test_lotel_fixer.py]]
