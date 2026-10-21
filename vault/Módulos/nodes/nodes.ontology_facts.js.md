---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/ontology_facts.js"
lenguaje: "javascript"
lineas: 99
aliases: ["nodes/ontology_facts.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/ontology_facts.js

> Datos · capa [[Capa Datos del catálogo]] · 99 líneas · `nodes/ontology_facts.js`

## Para qué sirve

Hechos tipados de la ontología (Khipus AI Finance) Relaciones reales empresa↔objeto y objeto↔objeto, con tipo de relación (rel) y ventana temporal. Se anexan a TEMPORAL_SEED_FACTS. Los ids de empresa están verificados contra el catálogo; los ONT_\* vienen de ontology.js.

## Qué datos contiene

- ~58 objetos con `id` (empresas, hechos u objetos)
- 13 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.TEMPORAL_SEED_FACTS`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **48 de 103** (línea 3107), después de [[nodes.ontology.js]] y antes de [[nodes.legal_names.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 48)
- [[engine.maptime.js]] — usa `TEMPORAL_SEED_FACTS`
- [[engine.temporal-graph.js]] — usa `TEMPORAL_SEED_FACTS`
- [[engine.timeline3d.js]] — usa `TEMPORAL_SEED_FACTS`
- [[scripts.build_graph_review.py]] — lo nombra por su ruta
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
