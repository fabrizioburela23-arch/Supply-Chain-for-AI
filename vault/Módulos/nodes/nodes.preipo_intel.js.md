---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/preipo_intel.js"
lenguaje: "javascript"
lineas: 104
aliases: ["nodes/preipo_intel.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/preipo_intel.js

> Datos · capa [[Capa Datos del catálogo]] · 104 líneas · `nodes/preipo_intel.js`

## Para qué sirve

Inteligencia de empresas privadas / pre-IPO (Khipu Finance) Datos de financiación, inversores, timeline a IPO e hitos para el panel de empresa privada (Fase 4). Indexado por id de nodo. Los nodos sin entrada aquí muestran el panel con la info disponible en el propio nodo (graceful). `investors` que coincidan con un id de nodo se enlazan al grafo.

## Qué datos contiene

- ~56 entradas con clave
- 5 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.PREIPO_INTEL`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **14 de 104** (línea 1520), después de [[nodes.nodes_multicapa.js]] y antes de [[nodes.listing_status.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 14)
- [[engine.app_main.js]] — usa `PREIPO_INTEL`
- [[engine.fincard.js]] — usa `PREIPO_INTEL`
- [[engine.portfolios.js]] — usa `PREIPO_INTEL`
- [[engine.temporal-graph.js]] — usa `PREIPO_INTEL`
- [[nodes.private_valuations.js]] — usa `PREIPO_INTEL`
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
