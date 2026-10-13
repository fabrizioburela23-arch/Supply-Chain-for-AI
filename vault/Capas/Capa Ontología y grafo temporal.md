---
tipo: "capa"
capa: "Ontología y grafo temporal"
archivos: 26
tags: ["capa/ontologia", "tipo/capa"]
---

# Capa Ontología y grafo temporal

> La fuente de verdad del grafo: eventos bitemporales en Postgres, acciones auditadas, reconciliación y el tiempo en el mapa.

**26 archivos · 11.218 líneas.** Volver al [[00 Mapa de Khipus]].

## Archivos

- [[engine.temporal-graph.js]] — 1.497 líneas · Grafo de Conocimiento Temporal (Khipus AI Finance) Reemplaza la vista 3D. Cada hecho tiene ventana de validez (valid_from → valid_until). Un timeline …
- [[ontology.api.py]] — 1.220 líneas · API REST de la ontología: /api/ontology/\*
- [[ontology.agents.py]] — 976 líneas · Fase 3: agentes que observan la ontología y PROPONEN Acciones. Nada se ejecuta sin aprobación humana (salvo lo que el usuario marque como …
- [[ontology.actions.py]] — 842 líneas · Fase 2 del roadmap: Acciones, el ADN de "escritura auditada" de Palantir. El usuario deja de solo mirar: registra tesis, anotaciones, correcciones y …
- [[ontology.reconcile.py]] — 790 líneas · G3 (misión de reparación 2026-10-04): RECONCILIACIÓN append-only entre el catálogo (data/grafo_v0.json, la verdad del MAPA/MCP) y Postgres (la verdad …
- [[ontology.service.py]] — 686 líneas · lógica de negocio de la ontología.
- [[scripts.audit_graph.py]] — 614 líneas · Auditoría automática del grafo (misión de reparación, G1).
- [[scripts.migrate_v0_to_ontology.py]] — 503 líneas · Fase 1: migra data/grafo_v0.json (el snapshot congelado en Fase 0) a la ontología (Postgres, tabla events + vistas materializadas objects/links).
- [[engine.maptime.js]] — 389 líneas · EL TIEMPO DENTRO DEL MAPA PRINCIPAL (2026-09-25) Fabrizio: "el grafo temporal y el normal deberían ser uno; el temporal no da mucho por sí solo". …
- [[ontology.timeline.py]] — 331 líneas · Phase 1 · M5: la línea de tiempo de una entidad.
- [[ontology.provenance.py]] — 285 líneas · Phase 1 · M1: procedencia de primera clase.
- [[core.entities.py]] — 282 líneas · Phase 1 · M2: identidad de entidad en el servidor.
- [[engine.hypergraph.js]] — 273 líneas · Hipergrafos temporales agénticos para Khipu Finance Una hiper-arista conecta MÚLTIPLES nodos a la vez (un evento que afecta a N empresas) y tiene …
- [[ontology.db.py]] — 268 líneas · conexión a Postgres (fuente única de verdad de la ontología).
- [[ontology.vocabulary.json]] — 256 líneas · REGISTRO ÚNICO del vocabulario del grafo. Añadir un tipo de objeto, un tipo de relación o un sector se hace AQUÍ (dato), no editando código en 29 …
- [[engine.reconcile.js]] — 254 líneas · G3 (misión de reparación 2026-10-04) 🩺 Diagnóstico → "Grafo: base vs catálogo". Muestra el dry-run de ontology/reconcile.py (GET …
- [[engine.timeline3d.js]] — 254 líneas · El Grafo Temporal en 3D, donde la PROFUNDIDAD ES EL TIEMPO.
- [[ontology.vocabulary.py]] — 253 líneas · REGISTRO ÚNICO del vocabulario del grafo.
- [[engine.secondbrain.js]] — 241 líneas · Second Brain de 5 capas para Khipu Finance Al seleccionar una empresa, abre un panel con 5 capas de conocimiento: 1. Mercado (precio + sparkline + …
- [[ontology.ledger_models.py]] — 226 líneas · el LIBRO DE DECISIONES (docs/INFRA_OPERATIVA.md §2.1; paso 6 del plan).
- [[ontology.bulk_import.py]] — 213 líneas · ingesta masiva idempotente y validada (Wikidata/GLEIF).
- [[ontology.ingest_news.py]] — 205 líneas · Phase 1 · M4: las noticias entran al grafo.
- [[ontology.models.py]] — 197 líneas · esquema SQLAlchemy de la ontología.
- [[scripts.reconcile_v0_to_ontology.py]] — 101 líneas · G3: reconciliar el catálogo (data/grafo_v0.json) con la ontología en Postgres SIN borrar nada.
- [[ontology.governance_models.py]] — 62 líneas · REGISTRO DE GOBERNANZA (docs/INFRA_OPERATIVA.md §5.1; paso 9 del plan).
- [[ontology.__init__.py]] — 0 líneas

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| usa a | [[Capa Infraestructura]] | 28 |
| la usa | [[Capa Infraestructura]] | 20 |
| usa a | [[Capa Datos del catálogo]] | 20 |
| la usa | [[Capa Investigación]] | 15 |
| la usa | [[Capa MCP y API]] | 11 |
| la usa | [[Capa Chat y agentes]] | 10 |
| la usa | [[Capa Interfaz (Khipus OS)]] | 9 |
| la usa | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 9 |
| usa a | [[Capa Interfaz (Khipus OS)]] | 9 |
| la usa | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 8 |
| la usa | [[Capa Comité]] | 6 |
| la usa | [[Capa Dinero (carteras, trading, corretaje)]] | 6 |
| usa a | [[Capa Investigación]] | 4 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 3 |
| usa a | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 2 |
| usa a | [[Capa Dinero (carteras, trading, corretaje)]] | 2 |
| usa a | [[Capa MCP y API]] | 1 |
