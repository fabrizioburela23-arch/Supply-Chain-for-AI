---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/context_engine.py"
lenguaje: "python"
lineas: 797
aliases: ["core/context_engine.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/context_engine.py

> Módulo · capa [[Capa Infraestructura]] · 797 líneas · `core/context_engine.py`

## Para qué sirve

EL motor de contexto (ARQUITECTURA_V2 §13; BRECHAS bloque 4: L4-01, L4-05, L4-10).

## API pública

- `detect(text, limit=…, resolve_short=…)` — Ids del grafo mencionados en `text`, en orden de aparición (sin repetir). _(línea 152)_
- `canon(x, umbral=…)` — Texto/ticker/id/alias → id CANÓNICO del grafo, o None (core/entities.resolve, umbral de BÚSQUEDA). _(línea 194)_
- `intent(text)` _(línea 223)_
- `flow(view=…)` _(línea 331)_
- `ppr(f, seeds, orientation=…)` — PageRank personalizado desde las semillas (vector numpy, máx = 1 fuera de las semillas). Caché LRU por generación (64 consultas). _(línea 347)_
- `relevance(seeds, question=…, intent_name=…, direction=…, view=…)` — → (R: dict id→R en [0,1] solo para nodos con R>0, info). Semillas = ids canónicos. _(línea 385)_
- `edge_score(R, e)` _(línea 413)_
- `pack(items, budget, eligible=…, on_choose=…)` — items: [{'key', 'R', 'cost', 'groups': [(clave, sim)]}] → (elegidos en orden de elección, descartados). _(línea 426)_
- `tail_summary(omitted, meta_of, lang=…)` — Estadísticos suficientes de lo que NO entró: conteo, % del peso, máximo, por salto, por tipo, países. _(línea 501)_
- `pack_edges(edges, seeds, question=…, budget_chars=…, direction=…, view=…, max_nodes=…)` — Aristas candidatas (dicts con source/target/type/w/conf/hop/direction) → (filas elegidas ordenadas por R(e|Q), cola, R). Coherencia de … _(línea 541)_
- `subgraph(seeds, question=…, depth=…, direction=…, budget_chars=…, include_partners=…, min_weight=…, min_conf=…, max_nodes=…, view=…)` — Vecindario de FLUJO de las semillas hasta `depth` saltos, ordenado por R(v|Q)/R(e|Q) y recortado al presupuesto, con la cola resumida. Las … _(línea 634)_
- `pack_supply_chain(res, question=…, budget_chars=…)` — Un resultado de get_supply_chain (MCP) → el MISMO resultado con `edges` ordenadas por R(e|Q) y recortadas al presupuesto (los 2 saltos … _(línea 708)_
- `rank_neighbors(nid, side, limit=…, question=…, view=…)` — Vecinos de FLUJO de `nid` ('up' proveedores / 'down' clientes) ordenados por R(e|Q). → [arista] _(línea 742)_
- clase `FactBook` — Tabla de hechos de UNA respuesta: cada resultado que se le da a la IA lleva un id [F#] con su fuente y as_of. `public()` = lo que va en la … _(línea 759)_
- `result_source(res)` — (fuente, as_of) declarados por un resultado de herramienta (primer nivel). _(línea 785)_

**Internas** (empiezan con `_`): `_collapse`, `_detector`, `_fuzzy_hits`, `_Flow`, `_trust`, `_build_flow`, `_orientation`, `_jlen`, `_edge_row`, `_meta_fn`, `_now_iso`

## Depende de

- [[core.__init__.py]] — importa `hot`
- [[core.countries.py]] — importa `countries`
- [[core.entities.py]] — importa `UMBRAL_BUSQUEDA`, `get_index`, `resolve`
- [[ontology.vocabulary.py]] — importa `UNVERIFIED_CONF`, `UNVERIFIED_RX`, `flow_relation_types`

## Lo usan

- [[core.khipu_chat.py]] — lo importa
- [[core.live_facts.py]] — lo importa
- [[core.semantic.py]] — lo importa
- [[mcp_server.contract.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- [[research.context.py]] — lo importa
- [[scripts.bench_scale.py]] — lo importa
- herramienta MCP `get_subgraph` → [[API herramientas MCP]]
- herramienta MCP `run_scenario` → [[API herramientas MCP]]

_Además lo importan 3 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_alias_voz_paridad.py]]
- [[tests.test_context_engine.py]]
- [[tests.test_countries.py]]
