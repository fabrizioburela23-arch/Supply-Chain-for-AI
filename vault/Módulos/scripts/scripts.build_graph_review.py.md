---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "scripts/build_graph_review.py"
lenguaje: "python"
lineas: 799
aliases: ["scripts/build_graph_review.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# scripts/build_graph_review.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 799 líneas · `scripts/build_graph_review.py`

## Para qué sirve

LISTAS DE REVISIÓN DEL GRAFO para Fabrizio (BRECHAS_V2 bloque 5; decisiones #6 #7 #8 #10).

## API pública

- `load_snapshot(path=…)` _(línea 135)_
- `load_origins()` — [s, t, type, w, arreglo] por fila CRUDA del catálogo (scripts/link_origins.js, mismo cargador que el export). _(línea 140)_
- `weight_proposals(links, origins, vocab)` — Una propuesta en [0,1] por vínculo del snapshot. Reglas (L3-11 + PROP-14): scale_1_6 → w/6 (todo arreglo salvo LINKS_EXPAND5, y los w>1 de … _(línea 175)_
- `build(snap, origins, vocab=…, fact_texts=…)` _(línea 235)_
- `render_md(rv)` _(línea 520)_
- `render_json(rv)` _(línea 729)_
- `reconcile_summary(plan)` — Plan de ontology/reconcile.build_plan → líneas en español simple (no se guarda en el documento). _(línea 734)_
- `live_reconcile()` _(línea 752)_
- `main(argv=…)` _(línea 764)_

**Internas** (empiezan con `_`): `_n`, `_cell`, `_arrow`, `_fact_files`, `_fact_file_of`, `_is_energy`, `_ck`

## Depende de

- [[ontology.db.py]] — importa `session_scope`
- [[ontology.reconcile.py]] — importa `reconcile`
- [[scripts.audit_graph.py]] — importa `audit_graph`
- [[data.grafo_v0.json]] — lo nombra por su ruta
- [[nodes.links_all.js]] — lo nombra por su ruta
- [[nodes.links_connect.js]] — lo nombra por su ruta
- [[nodes.links_expand.js]] — lo nombra por su ruta
- [[nodes.nodes_china.js]] — lo nombra por su ruta
- [[nodes.nodes_expand4.js]] — lo nombra por su ruta
- [[nodes.nodes_expand5.js]] — lo nombra por su ruta
- [[nodes.nodes_multicapa.js]] — lo nombra por su ruta
- [[nodes.nodes_nuclear.js]] — lo nombra por su ruta
- [[nodes.nodes_seed.js]] — lo nombra por su ruta
- [[nodes.ontology_facts.js]] — lo nombra por su ruta
- [[nodes.temporal_seed_facts.js]] — lo nombra por su ruta
- [[nodes.temporal_seed_facts2.js]] — lo nombra por su ruta

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

_Además lo importan 1 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV DATABASE_URL]]

## Pruebas que lo cubren

- [[tests.test_review_lists.py]]
