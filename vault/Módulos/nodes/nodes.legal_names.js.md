---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/legal_names.js"
lenguaje: "javascript"
lineas: 191
aliases: ["nodes/legal_names.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/legal_names.js

> Datos · capa [[Capa Datos del catálogo]] · 191 líneas · `nodes/legal_names.js`

## Para qué sirve

NOMBRES LEGALES y nombres alternativos → id del grafo (Phase 1 · M2, pendiente "Enriquecer alias con nombres legales completos").

## Qué datos contiene

- 7 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.LEGAL_NAMES`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **42 de 91** (línea 7826), después de [[nodes.ontology_facts.js]] y antes de [[engine.temporal-graph.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 42)
- [[engine.khipu_chat.js]] — usa `LEGAL_NAMES`
- [[engine.resolve.js]] — usa `LEGAL_NAMES`
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

- [[tests.test_entities.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-27 (b) — Nombres - búsqueda por nombre legal + etiquetas legibles (sw v137)]]
