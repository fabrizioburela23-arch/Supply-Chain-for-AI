---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/legal_names.js"
lenguaje: "javascript"
lineas: 281
aliases: ["nodes/legal_names.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/legal_names.js

> Datos · capa [[Capa Datos del catálogo]] · 281 líneas · `nodes/legal_names.js`

## Para qué sirve

NOMBRES LEGALES y nombres alternativos → id del grafo (Phase 1 · M2, pendiente "Enriquecer alias con nombres legales completos").

## Qué datos contiene

- 13 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.LEGAL_NAMES`, `window.RESOLVE_STOPWORDS`, `window.VOICE_ALIASES`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **48 de 101** (línea 3107), después de [[nodes.ontology_facts.js]] y antes de [[engine.temporal-graph.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 48)
- [[engine.catalog_sync.js]] — usa `LEGAL_NAMES`
- [[engine.khipu_chat.js]] — usa `LEGAL_NAMES`
- [[engine.resolve.js]] — usa `LEGAL_NAMES`, `RESOLVE_STOPWORDS`, `VOICE_ALIASES`
- [[engine.voice.js]] — usa `LEGAL_NAMES`
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

- [[tests.test_alias_voz_paridad.py]]
- [[tests.test_entities.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (k) — FASE 2+ LOTE I - rutas con decisión, CSP estricta, riesgo]]
- [[Sesión 2026-09-27 (b) — Nombres - búsqueda por nombre legal + etiquetas legibles (sw v137)]]
