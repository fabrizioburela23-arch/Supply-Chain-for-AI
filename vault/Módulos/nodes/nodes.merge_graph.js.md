---
tipo: "modulo"
capa: "Datos del catálogo"
ruta: "nodes/merge_graph.js"
lenguaje: "javascript"
lineas: 207
aliases: ["nodes/merge_graph.js"]
tags: ["capa/datos-catalogo", "tipo/modulo"]
---

# nodes/merge_graph.js

> Módulo · capa [[Capa Datos del catálogo]] · 207 líneas · `nodes/merge_graph.js`

## Para qué sirve

EL merge del catálogo (única implementación) Usado por app.html (navegador) Y por scripts/export_graph_v0.js (Node vm). Antes esta lógica existía 3 veces (app.html inline, exportador por líneas hardcodeadas y script de migración) y divergía en silencio.

## API pública (globales que define)

`window.buildKhipusGraph`, `window.linkTrust`

De nivel superior (globales del script): `UNVERIFIED_CONF`, `UNVERIFIED_QUALIFIER_RX`, `UNVERIFIED_RX`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **20 de 104** (línea 1526), después de [[nodes.links_connect.js]] y antes de [[engine.catalog_sync.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 20)
- [[engine.app_main.js]] — usa `buildKhipusGraph`
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta
- [[scripts.link_origins.js]] — lo nombra por su ruta

## Pruebas que lo cubren

- [[tests.test_app_split.py]]
- [[tests.test_catalog_api_client.py]]
- [[tests.test_merge_graph_alias.py]]
- [[tests.test_repair_graph.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-04 (h) — MISIÓN DE REPARACIÓN P0 INVESTIGACIÓN (R1-R6, sw v201)]]
- [[Sesión 2026-09-28 (c) — DOSSIER PARA TODAS LAS EMPRESAS + DATOS EN VIVO (sw v151)]]
- [[Sesión 2026-09-28 (b) — Estado en bolsa VERIFICADO (sw v142-143)]]
- [[Sesión 2026-07-06 — Etapa 2 — Datos limpios - COMPLETA (5 batches publicados)]]
