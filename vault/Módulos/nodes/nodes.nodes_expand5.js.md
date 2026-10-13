---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/nodes_expand5.js"
lenguaje: "javascript"
lineas: 2425
aliases: ["nodes/nodes_expand5.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/nodes_expand5.js

> Datos · capa [[Capa Datos del catálogo]] · 2.425 líneas · `nodes/nodes_expand5.js`

## Para qué sirve

Informe de enriquecimiento 2026-07 Generado por scripts/ingest_enrichment_md.py desde el informe de Fabrizio (148 nuevas + 82 enriquecidas). NO editar a mano: regenerar con el script.

## Qué datos contiene

- ~627 filas de vínculos (`[origen, destino, …]` o `{s, t}`)
- 327 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.LINKS_EXPAND5`, `window.META_EXPAND5`, `window.NODES_EXPAND5`

## Depende de

- [[nodes.nodes_seed.js]] — usa `CATS_NEW`, `CAT_TO_SECTOR`, `NODE_META`

Se carga en [[app.html]] en la posición **9 de 95** (línea 1444), después de [[nodes.nodes_expand4.js]] y antes de [[nodes.meta_fill.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 9)
- [[app.html]] — usa `LINKS_EXPAND5`, `NODES_EXPAND5`
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
