---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/ontology.js"
lenguaje: "javascript"
lineas: 80
aliases: ["nodes/ontology.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/ontology.js

> Datos · capa [[Capa Datos del catálogo]] · 80 líneas · `nodes/ontology.js`

## Para qué sirve

Ontología (estilo Palantir) para Khipus AI Finance Define TIPOS DE OBJETO (más allá de "empresa") y TIPOS DE RELACIÓN tipadas, además de los objetos no-empresa (tecnologías, políticas, países, energía, materiales, productos, organismos). Las empresas siguen viniendo de NODE_BY_ID. El Grafo Temporal resuelve entidades desde NODE_BY_ID + ONTOLOGY._byId.

## Qué datos contiene

- ~32 objetos con `id` (empresas, hechos u objetos)
- 5 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.ONTOLOGY`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **42 de 95** (línea 7843), después de [[nodes.temporal_seed_facts2.js]] y antes de [[nodes.ontology_facts.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 42)
- [[engine.maptime.js]] — usa `ONTOLOGY`
- [[engine.temporal-graph.js]] — usa `ONTOLOGY`
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
