---
tipo: "modulo"
capa: "Datos del catálogo"
ruta: "scripts/export_graph_v0.js"
lenguaje: "javascript"
lineas: 104
aliases: ["scripts/export_graph_v0.js"]
tags: ["capa/datos-catalogo", "tipo/modulo"]
---

# scripts/export_graph_v0.js

> Módulo · capa [[Capa Datos del catálogo]] · 104 líneas · `scripts/export_graph_v0.js`

## Para qué sirve

Exporta el grafo canónico a data/grafo_v0.json v2 (Etapa 2, 2026-07): carga los nodes/\*.js reales en un sandbox vm y usa LA MISMA función de merge que el navegador (nodes/merge_graph.js). La versión anterior ejecutaba app.html por rangos de línea HARDCODEADOS que se desfasaban con cada edición — eliminada.

## API pública (globales que define)

De nivel superior (globales del script): `DATA_FILES`, `ROOT`, `buildSnapshot`, `fs`, `path`, `vm`

## Depende de

- [[nodes.legal_names.js]] — lo nombra por su ruta
- [[nodes.links_all.js]] — lo nombra por su ruta
- [[nodes.links_connect.js]] — lo nombra por su ruta
- [[nodes.links_expand.js]] — lo nombra por su ruta
- [[nodes.listing_status.js]] — lo nombra por su ruta
- [[nodes.merge_graph.js]] — lo nombra por su ruta
- [[nodes.nodes_china.js]] — lo nombra por su ruta
- [[nodes.nodes_expand.js]] — lo nombra por su ruta
- [[nodes.nodes_expand2.js]] — lo nombra por su ruta
- [[nodes.nodes_expand3.js]] — lo nombra por su ruta
- [[nodes.nodes_expand4.js]] — lo nombra por su ruta
- [[nodes.nodes_expand5.js]] — lo nombra por su ruta
- [[nodes.nodes_multicapa.js]] — lo nombra por su ruta
- [[nodes.nodes_nuclear.js]] — lo nombra por su ruta
- [[nodes.nodes_seed.js]] — lo nombra por su ruta
- [[nodes.nodes_spacex.js]] — lo nombra por su ruta
- [[nodes.ontology.js]] — lo nombra por su ruta
- [[nodes.ontology_facts.js]] — lo nombra por su ruta
- [[nodes.preipo_intel.js]] — lo nombra por su ruta
- [[nodes.private_valuations.js]] — lo nombra por su ruta
- [[nodes.temporal_seed_facts.js]] — lo nombra por su ruta
- [[nodes.temporal_seed_facts2.js]] — lo nombra por su ruta

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Pruebas que lo cubren

- [[tests.test_alias_voz_paridad.py]]
- [[tests.test_graph_audit.py]]
- [[tests.test_merge_graph_alias.py]]
- [[tests.test_ontology.py]]
- [[tests.test_repair_graph.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-27 (b) — Nombres - búsqueda por nombre legal + etiquetas legibles (sw v137)]]
- [[Sesión 2026-07-06 — Etapa 2 — Datos limpios - COMPLETA (5 batches publicados)]]
