---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/temporal_seed_facts2.js"
lenguaje: "javascript"
lineas: 98
aliases: ["nodes/temporal_seed_facts2.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/temporal_seed_facts2.js

> Datos · capa [[Capa Datos del catálogo]] · 98 líneas · `nodes/temporal_seed_facts2.js`

## Para qué sirve

Hechos temporales adicionales (Khipus AI Finance) Segunda tanda de hechos reales y verificados (2016–2026) de la cadena IA / semis / nuclear / espacio. Se anexan a window.TEMPORAL_SEED_FACTS. Todos los ids de 'object_type:node' están verificados contra el catálogo de nodos existente. Esquema idéntico al de temporal_seed_facts.js.

## Qué datos contiene

- ~23 objetos con `id` (empresas, hechos u objetos)
- 9 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.TEMPORAL_SEED_FACTS`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **41 de 95** (línea 7840), después de [[nodes.temporal_seed_facts.js]] y antes de [[nodes.ontology.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 41)
- [[engine.maptime.js]] — usa `TEMPORAL_SEED_FACTS`
- [[engine.temporal-graph.js]] — usa `TEMPORAL_SEED_FACTS`
- [[engine.timeline3d.js]] — usa `TEMPORAL_SEED_FACTS`
- [[scripts.build_graph_review.py]] — lo nombra por su ruta
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
