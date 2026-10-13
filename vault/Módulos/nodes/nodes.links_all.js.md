---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/links_all.js"
lenguaje: "javascript"
lineas: 39
aliases: ["nodes/links_all.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/links_all.js

> Datos · capa [[Capa Datos del catálogo]] · 39 líneas · `nodes/links_all.js`

## Para qué sirve

Links del ecosistema SpaceX y conexiones expandidas

## Qué datos contiene

- ~32 filas de vínculos (`[origen, destino, …]` o `{s, t}`)
- 2 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

De nivel superior (globales del script): `LINKS_SPACEX`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **16 de 96** (línea 1451), después de [[nodes.private_valuations.js]] y antes de [[nodes.links_expand.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 16)
- [[app.html]] — usa `LINKS_SPACEX`
- [[scripts.build_graph_review.py]] — lo nombra por su ruta
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
