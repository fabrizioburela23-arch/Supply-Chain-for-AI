---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/nodes_expand4.js"
lenguaje: "javascript"
lineas: 63
aliases: ["nodes/nodes_expand4.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/nodes_expand4.js

> Datos · capa [[Capa Datos del catálogo]] · 63 líneas · `nodes/nodes_expand4.js`

## Para qué sirve

Infraestructura espacial (Khipu Finance) Completa el sector espacio del documento de expansión: landers lunares, estructuras en microgravedad, plano espacial y estación comercial.

## Qué datos contiene

- ~5 filas de vínculos (`[origen, destino, …]` o `{s, t}`)
- 4 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.LINKS_EXPAND4`, `window.NODES_EXPAND4`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **8 de 93** (línea 1443), después de [[nodes.nodes_nuclear.js]] y antes de [[nodes.nodes_expand5.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 8)
- [[app.html]] — usa `LINKS_EXPAND4`, `NODES_EXPAND4`
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
