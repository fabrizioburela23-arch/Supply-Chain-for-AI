---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/nodes_multicapa.js"
lenguaje: "javascript"
lineas: 1669
aliases: ["nodes/nodes_multicapa.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/nodes_multicapa.js

> Datos · capa [[Capa Datos del catálogo]] · 1.669 líneas · `nodes/nodes_multicapa.js`

## Para qué sirve

EXPANSIÓN MULTICAPA (doc de Fabrizio, ago-2026): 381 nodos en 6 capas (energía, materiales, macro/crédito, inmobiliario, logística, actores) + sus links. Generado por scripts/ingest_multicapa.py — NO editar a mano: regenerar con el script. Reconciliación aplicada (Calpine→ Constellation, DB_Schenker fuera, colisiones contra el grafo real omitidas).

## Qué datos contiene

- ~874 filas de vínculos (`[origen, destino, …]` o `{s, t}`)
- ~352 entradas con clave
- 808 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.LINKS_MULTICAPA`, `window.NODES_MULTICAPA`

De nivel superior (globales del script): `META_MULTICAPA`, `_MC_C2S`, `_MC_S9`

## Depende de

- [[nodes.nodes_seed.js]] — usa `CATS`, `CATS_NEW`, `CAT_TO_SECTOR`, `NODE_META`, `SECTORS9`

Se carga en [[app.html]] en la posición **12 de 93** (línea 1447), después de [[nodes.nodes_china.js]] y antes de [[nodes.preipo_intel.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 12)
- [[app.html]] — usa `LINKS_MULTICAPA`, `NODES_MULTICAPA`
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta
- [[scripts.ingest_multicapa.py]] — lo nombra por su ruta

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (gg) — DIRECCIONES AL REVÉS + PESO DE LICENCIAS + PISO DEL KERNEL]]
- [[Sesión 2026-09-27 (b) — Nombres - búsqueda por nombre legal + etiquetas legibles (sw v137)]]
- [[Sesión 2026-08-02 — Expansión multicapa COMPLETA (olas 1-6) - 949 nodos, 13 sectores, 70]]
