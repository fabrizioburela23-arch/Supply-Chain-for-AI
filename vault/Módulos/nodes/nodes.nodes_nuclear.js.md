---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/nodes_nuclear.js"
lenguaje: "javascript"
lineas: 150
aliases: ["nodes/nodes_nuclear.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/nodes_nuclear.js

> Datos · capa [[Capa Datos del catálogo]] · 150 líneas · `nodes/nodes_nuclear.js`

## Para qué sirve

Sector Energía Nuclear (Khipu Finance) SMR (reactores modulares pequeños) + Fusión + Uranio. La demanda 24/7 de energía de la IA es la tesis: los hyperscalers firman PPAs nucleares. Schema idéntico al resto del proyecto. Categorías: nuclear_smr, nuclear_fusion, uranium.

## Qué datos contiene

- ~11 filas de vínculos (`[origen, destino, …]` o `{s, t}`)
- 12 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.LINKS_NUCLEAR`, `window.NODES_NUCLEAR`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **8 de 103** (línea 1510), después de [[nodes.nodes_expand3.js]] y antes de [[nodes.nodes_expand4.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 8)
- [[engine.app_main.js]] — usa `LINKS_NUCLEAR`, `NODES_NUCLEAR`
- [[scripts.build_graph_review.py]] — lo nombra por su ruta
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
