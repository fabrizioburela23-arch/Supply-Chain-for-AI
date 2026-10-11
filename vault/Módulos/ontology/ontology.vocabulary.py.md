---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/vocabulary.py"
lenguaje: "python"
lineas: 251
aliases: ["ontology/vocabulary.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/vocabulary.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 251 líneas · `ontology/vocabulary.py`

## Para qué sirve

REGISTRO ÚNICO del vocabulario del grafo.

## API pública

- `load(force=…)` — Carga vocabulary.json (cacheado por mtime → recarga sola al editarlo). _(línea 64)_
- `object_types()` _(línea 89)_
- `economic_types()` — Lista BLANCA de tipos que SÍ son nodos del grafo económico. _(línea 93)_
- `non_economic_types()` _(línea 98)_
- `is_economic(otype)` — ¿Este tipo es nodo del grafo? Lo DESCONOCIDO se excluye (seguro para el grafo) pero se REPORTA — nunca se cuela ni se degrada en silencio. _(línea 102)_
- `relation_types_all()` _(línea 113)_
- `relation_types()` — Relaciones ESTRUCTURALES (las que propagan daño y forman las matrices). _(línea 117)_
- `relation_weights()` _(línea 127)_
- `flow_relation_types()` — Relaciones de FLUJO (flow=true en vocabulary.json), en el orden del JSON. Si el JSON no marca ninguna (versión vieja), cae a la lista … _(línea 145)_
- `text_says_unverified(text)` — ¿El texto curado dice que la RELACIÓN no está verificada? (no una cifra o una nota) _(línea 167)_
- `is_flow_relation(rel)` _(línea 172)_
- `flow_degree(links)` — Grado ESTRUCTURAL por nodo: número de pares distintos source→target unidos por una relación de flujo (un par con supply+fab cuenta UNA vez; … _(línea 176)_
- `symmetric_relations()` _(línea 199)_
- `is_known_relation(rel)` _(línea 204)_
- `source_kinds()` _(línea 211)_
- `note_unknown(kind, value)` — Registra un valor fuera del vocabulario. Loguea la PRIMERA vez y lleva la cuenta, para que aparezca en /api/vocabulary/unknown y en … _(línea 216)_
- `unknown_report()` _(línea 229)_
- `reset_unknown()` _(línea 233)_
- `snapshot()` — Vocabulario completo para servir al cliente (mata las copias duplicadas). _(línea 238)_

**Internas** (empiezan con `_`): `_path`

## Depende de

- [[ontology.vocabulary.json]] — lo nombra por su ruta

## Lo usan

- [[core.portfolio_ai.py]] — lo importa
- [[core.semantic.py]] — lo importa
- [[core.world.py]] — lo importa
- [[matrix.engine.py]] — lo importa
- [[matrix.tensor.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[ontology.agents.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[ontology.provenance.py]] — lo importa
- [[ontology.service.py]] — lo importa
- [[research.context.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `get_company` → [[API herramientas MCP]]
- herramienta MCP `get_supply_chain` → [[API herramientas MCP]]
- herramienta MCP `run_committee` → [[API herramientas MCP]]
- herramienta MCP `run_research` → [[API herramientas MCP]]
- herramienta MCP `search_companies` → [[API herramientas MCP]]

_Además lo importan 4 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_cleanup_nrs_parity.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_vocabulary.py]]
