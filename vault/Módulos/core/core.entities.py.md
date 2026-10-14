---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "core/entities.py"
lenguaje: "python"
lineas: 492
aliases: ["core/entities.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# core/entities.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 492 líneas · `core/entities.py`

## Para qué sirve

Phase 1 · M2: identidad de entidad en el servidor.

## API pública

- `norm(txt)` — minúsculas + sin acentos + sin puntuación + espacios colapsados. _(línea 60)_
- `strip_suffix(txt)` — Quita sufijos societarios finales ('nvidia corporation' → 'nvidia'). _(línea 72)_
- `parse_ticker(raw)` — El campo `ticker` del catálogo mezcla símbolo y bolsa: 'RGTI · Nasdaq', 'IBM · NYSE (división)'. Devuelve (simbolo, bolsa) — solo la parte … _(línea 80)_
- `external_ids(node)` — Identificadores externos estructurados de un nodo del catálogo. `mkt` es el símbolo limpio; `ticker` trae símbolo + bolsa mezclados. _(línea 96)_
- `get_index(force=…, snapshot_path=…)` — Índice de la generación VIGENTE (se reconstruye solo si cambió). `snapshot_path` = un archivo aparte (no toca el índice compartido). _(línea 199)_
- `graph_version()` — La generación del grafo que usa este módulo (tests/test_ops_single_source.py). _(línea 216)_
- `entity_ids_for(eid)` — [eid] + los ids VIEJOS (alias del catálogo y fusiones) que hoy apuntan a eid. Revisión G1b/G1d: lo guardado con un id que luego se fusionó … _(línea 221)_
- `resolve(texto, umbral=…)` — Resuelve un texto libre a una entidad del grafo. _(línea 234)_
- `search_scores(query)` — Búsqueda de empresas (MCP search_companies): {id: (puntaje, método)} con la escalera de siempre — resolve() con el umbral de búsqueda → … _(línea 439)_
- `resolve_many(textos, umbral=…)` — Resuelve una lista; devuelve (resueltos {texto: info}, no_resueltos[]). _(línea 483)_

**Internas** (empiezan con `_`): `_sin_marca`, `_build_index`, `_trigramas`, `_Claves`, `_indice_resolver`, `_indice_busqueda`, `_puntaje_nodo`

## Depende de

- [[core.__init__.py]] — importa `hot`

## Lo usan

- [[core.agents_api.py]] — lo importa
- [[core.context_engine.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa
- [[core.live_caps.py]] — lo importa
- [[core.live_facts.py]] — lo importa
- [[core.portfolio_advisor.py]] — lo importa
- [[core.portfolio_ai.py]] — lo importa
- [[core.space.py]] — lo importa
- [[matrix.tensor.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[ontology.agents.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[research.api.py]] — lo importa
- [[research.auto_events.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[research.context.py]] — lo importa
- [[research.outcomes.py]] — lo importa
- [[research.router.py]] — lo importa
- [[research.runner.py]] — lo importa
- [[scripts.bench_scale.py]] — lo importa
- herramienta MCP `calculate_correlation` → [[API herramientas MCP]]
- herramienta MCP `find_anomalies` → [[API herramientas MCP]]
- herramienta MCP `get_committee_memo` → [[API herramientas MCP]]
- herramienta MCP `get_company` → [[API herramientas MCP]]
- herramienta MCP `get_history` → [[API herramientas MCP]]
- herramienta MCP `get_ontology_object` → [[API herramientas MCP]]
- herramienta MCP `get_research` → [[API herramientas MCP]]
- herramienta MCP `get_supply_chain` → [[API herramientas MCP]]
- herramienta MCP `project_portfolio` → [[API herramientas MCP]]
- herramienta MCP `run_committee` → [[API herramientas MCP]]
- herramienta MCP `run_research` → [[API herramientas MCP]]
- herramienta MCP `search_companies` → [[API herramientas MCP]]

_Además lo importan 7 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_alias_voz_paridad.py]]
- [[tests.test_committee_os_narr.py]]
- [[tests.test_context_engine.py]]
- [[tests.test_entities.py]]
- [[tests.test_ops_single_source.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_scale_search.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (k) — FASE 2+ LOTE I - rutas con decisión, CSP estricta, riesgo]]
- [[Sesión 2026-09-27 (b) — Nombres - búsqueda por nombre legal + etiquetas legibles (sw v137)]]
- [[Sesión 2026-09-22 al 24 — PHASE 1 Live Investment Graph COMPLETA + velocidad + 3D temporal]]
