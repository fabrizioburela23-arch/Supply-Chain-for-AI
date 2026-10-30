---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/nodes_china.js"
lenguaje: "javascript"
lineas: 86
aliases: ["nodes/nodes_china.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/nodes_china.js

> Datos · capa [[Capa Datos del catálogo]] · 86 líneas · `nodes/nodes_china.js`

## Para qué sirve

Ola CHINA 2026-07 (pedido de Fabrizio tras la OPI de CXMT: "estamos desperdiciando el mercado chino"). 13 empresas + 21 links curados a mano con datos verificados a jul-2026. CXMT: OPI en el STAR Market de Shanghái el 27-jul-2026 — la mayor de Asia en 2026 (~US\$8.600M recaudados, debut ~+470%, 4º fabricante mundial de DRAM). Convención de links: source PROVEE a target (igual que todo el catálogo).

## Qué datos contiene

- ~22 filas de vínculos (`[origen, destino, …]` o `{s, t}`)
- ~13 entradas con clave
- 14 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.LINKS_CHINA`, `window.META_CHINA`, `window.NODES_CHINA`

## Depende de

- [[nodes.nodes_seed.js]] — usa `NODE_META`

Se carga en [[app.html]] en la posición **12 de 104** (línea 1518), después de [[nodes.meta_fill.js]] y antes de [[nodes.nodes_multicapa.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 12)
- [[engine.app_main.js]] — usa `LINKS_CHINA`, `NODES_CHINA`
- [[scripts.build_graph_review.py]] — lo nombra por su ruta
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
