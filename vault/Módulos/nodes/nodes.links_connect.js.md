---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/links_connect.js"
lenguaje: "javascript"
lineas: 186
aliases: ["nodes/links_connect.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/links_connect.js

> Datos · capa [[Capa Datos del catálogo]] · 186 líneas · `nodes/links_connect.js`

## Para qué sirve

Conexiones de cadena de suministro para nodos huérfanos Conecta los ~82 nodos que se habían añadido (expand2/expand3) sin enlaces, con relaciones reales verificadas. Formato: {s, t, w, rel, type} Convención (igual que links_expand.js): s = empresa, t = aquello de lo que depende (proveedor/fab/cloud/licencia aguas arriba) o su cliente (deploy/customer). type ∈ supply | fab | license | cloud | invest | deploy | partner | owns

## Qué datos contiene

- ~170 filas de vínculos (`[origen, destino, …]` o `{s, t}`)
- 12 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.LINKS_CONNECT`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **18 de 97** (línea 1453), después de [[nodes.links_expand.js]] y antes de [[nodes.merge_graph.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 18)
- [[app.html]] — usa `LINKS_CONNECT`
- [[scripts.build_graph_review.py]] — lo nombra por su ruta
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (gg) — DIRECCIONES AL REVÉS + PESO DE LICENCIAS + PISO DEL KERNEL]]
