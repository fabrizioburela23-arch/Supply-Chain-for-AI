---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/categories_extra.js"
lenguaje: "javascript"
lineas: 17
aliases: ["nodes/categories_extra.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/categories_extra.js

> Datos · capa [[Capa Datos del catálogo]] · 17 líneas · `nodes/categories_extra.js`

## Para qué sirve

GENERADO por scripts/build_categories.py desde data/categories.json. NO EDITAR A MANO: cambia el JSON y regenera. Se carga justo después de nodes/nodes_seed.js. 55 categorías nuevas (lote 2026-10-14) + 65 etiquetas ES/EN de categorías que mostraban su id crudo. Entra en CATS_NEW (engine/app_main.js la funde en CATS) y en CAT_TO_SECTOR SIN pisar lo que ya exista; nodes_multicapa.js solo rellena lo que falta, así que respeta estas etiquetas.

## Qué datos contiene

- 23 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.CATS_EXTRA`, `window.CATS_LABELS_FIX`, `window.CAT_ALIASES`, `window.CAT_TO_SECTOR_EXTRA`

## Depende de

- [[nodes.nodes_seed.js]] — usa `CATS`, `CATS_NEW`, `CAT_TO_SECTOR`

Se carga en [[app.html]] en la posición **3 de 100** (línea 1504), después de [[nodes.nodes_seed.js]] y antes de [[nodes.nodes_expand.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 3)
- [[scripts.build_categories.py]] — lo nombra por su ruta
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

- [[tests.test_catalog_fix_categories.py]]
- [[tests.test_import_adapter.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-14 (c) — LOTE K - IMPORTADOR DE EMPRESAS, PAÍSES ISO-2, CATEGORÍAS, CHAT]]
