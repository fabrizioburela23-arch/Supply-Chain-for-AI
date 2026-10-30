---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/temporal_seed_facts.js"
lenguaje: "javascript"
lineas: 96
aliases: ["nodes/temporal_seed_facts.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/temporal_seed_facts.js

> Datos · capa [[Capa Datos del catálogo]] · 96 líneas · `nodes/temporal_seed_facts.js`

## Para qué sirve

Hechos temporales curados (Khipus AI Finance) Grafo de Conocimiento Temporal: cada hecho tiene ventana de validez (valid_from → valid_until; null = vigente hoy). Datos reales de la cadena de suministro de semis / IA / espacio / nuclear, con fechas reales. object_type: 'node' (arista entre entidades) | 'literal' (atributo del sujeto). CONCAT (no asignación): así el orden de carga de los 3 archivos de hechos (este, temporal_seed_facts2.js, ontology_facts.js) da igual — antes, reordenar los &lt;script> perdía 58-81 hechos en silencio.

## Qué datos contiene

- ~24 objetos con `id` (empresas, hechos u objetos)
- 9 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.TEMPORAL_SEED_FACTS`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **45 de 104** (línea 3131), después de [[engine.canvas-data.js]] y antes de [[nodes.temporal_seed_facts2.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 45)
- [[engine.maptime.js]] — usa `TEMPORAL_SEED_FACTS`
- [[engine.temporal-graph.js]] — usa `TEMPORAL_SEED_FACTS`
- [[engine.timeline3d.js]] — usa `TEMPORAL_SEED_FACTS`
- [[scripts.build_graph_review.py]] — lo nombra por su ruta
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
