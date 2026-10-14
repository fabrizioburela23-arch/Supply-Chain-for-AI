---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/listing_status.js"
lenguaje: "javascript"
lineas: 2048
aliases: ["nodes/listing_status.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/listing_status.js

> Datos · capa [[Capa Datos del catálogo]] · 2.048 líneas · `nodes/listing_status.js`

## Para qué sirve

GENERADO por scripts/build_listing_status.py. Estado en bolsa VERIFICADO con fuente (salió a bolsa / comprada / fusionada / filial / cerró) de empresas que el catálogo daba por privadas. Lo aplica nodes/merge_graph.js (navegador y snapshot). No editar a mano: regenerar con una nueva verificación.

## Qué datos contiene

- ~213 entradas con clave
- 90 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.LISTING_STATUS`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **14 de 98** (línea 1449), después de [[nodes.preipo_intel.js]] y antes de [[nodes.private_valuations.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 14)
- [[engine.app_main.js]] — usa `LISTING_STATUS`
- [[scripts.build_listing_status.py]] — lo nombra por su ruta
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

- [[tests.test_committee_os_narr.py]]
- [[tests.test_entities.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-28 (b) — Estado en bolsa VERIFICADO (sw v142-143)]]
