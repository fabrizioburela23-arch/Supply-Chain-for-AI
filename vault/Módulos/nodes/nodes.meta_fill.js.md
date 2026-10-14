---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/meta_fill.js"
lenguaje: "javascript"
lineas: 1467
aliases: ["nodes/meta_fill.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/meta_fill.js

> Datos · capa [[Capa Datos del catálogo]] · 1.467 líneas · `nodes/meta_fill.js`

## Para qué sirve

Fichas generadas para las 187 empresas sin metadata (2026-07-12, workflow de 26 agentes: 13 generadores + 13 verificadores cruzados). Solo rellena HUECOS: nunca pisa un dato existente de NODE_META. Datos aproximados marcados con ~. Regenerable con el workflow fill-company-meta.

## Qué datos contiene

- 141 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.DESC_FILL`, `window.META_FILL`

## Depende de

- [[nodes.nodes_seed.js]] — usa `NODE_META`

Se carga en [[app.html]] en la posición **10 de 98** (línea 1445), después de [[nodes.nodes_expand5.js]] y antes de [[nodes.nodes_china.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 10)

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-28 (b) — Estado en bolsa VERIFICADO (sw v142-143)]]
- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
