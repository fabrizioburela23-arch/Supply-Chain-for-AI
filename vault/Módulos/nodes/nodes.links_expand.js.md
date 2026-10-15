---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/links_expand.js"
lenguaje: "javascript"
lineas: 413
aliases: ["nodes/links_expand.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/links_expand.js

> Datos · capa [[Capa Datos del catálogo]] · 413 líneas · `nodes/links_expand.js`

## Para qué sirve

Khipu Finance · Supply Chain Links for Expanded Nodes ~150+ meaningful supply chain links for nodes in nodes_expand.js and nodes_expand2.js Generated 2026-06

## Qué datos contiene

- ~404 filas de vínculos (`[origen, destino, …]` o `{s, t}`)
- 15 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

De nivel superior (globales del script): `LINKS_EXPAND`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **18 de 100** (línea 1519), después de [[nodes.links_all.js]] y antes de [[nodes.links_connect.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 18)
- [[engine.app_main.js]] — usa `LINKS_EXPAND`
- [[scripts.build_graph_review.py]] — lo nombra por su ruta
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

- [[tests.test_server_smoke.py]]
