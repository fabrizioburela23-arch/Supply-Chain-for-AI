---
tipo: "capa"
capa: "Ontología y grafo temporal"
archivos: 37
tags: ["capa/ontologia", "tipo/capa"]
---

# Capa Ontología y grafo temporal

> La fuente de verdad del grafo: eventos bitemporales en Postgres, acciones auditadas, reconciliación y el tiempo en el mapa.

**37 archivos · 19.097 líneas.** Volver al [[00 Mapa de Khipus]].

## Archivos

- [[ontology.company_import.py]] — 2.699 líneas · importador de fichas khipus.company/1 (docs/expansion/EXPANSION_5K.md, bloque E2).
- [[ontology.api.py]] — 2.007 líneas · API REST de la ontología: /api/ontology/\*
- [[engine.temporal-graph.js]] — 1.466 líneas · Grafo de Conocimiento Temporal (Khipus AI Finance) Reemplaza la vista 3D. Cada hecho tiene ventana de validez (valid_from → valid_until). Un timeline …
- [[ontology.agents.py]] — 1.039 líneas · Fase 3: agentes que observan la ontología y PROPONEN Acciones. Nada se ejecuta sin aprobación humana (salvo lo que el usuario marque como …
- [[ontology.actions.py]] — 906 líneas · Fase 2 del roadmap: Acciones, el ADN de "escritura auditada" de Palantir. El usuario deja de solo mirar: registra tesis, anotaciones, correcciones y …
- [[ontology.reconcile.py]] — 843 líneas · G3 (misión de reparación 2026-10-04): RECONCILIACIÓN append-only entre el catálogo (data/grafo_v0.json, la verdad del MAPA/MCP) y Postgres (la verdad …
- [[scripts.build_graph_review.py]] — 799 líneas · LISTAS DE REVISIÓN DEL GRAFO para Fabrizio (BRECHAS_V2 bloque 5; decisiones #6 #7 #8 #10).
- [[ontology.company_schema.py]] — 780 líneas · espejo Pydantic v2 de `data/import/company.schema.json` (khipus.company/1; E2.1).
- [[core.entities.py]] — 767 líneas · Phase 1 · M2: identidad de entidad en el servidor.
- [[ontology.service.py]] — 765 líneas · lógica de negocio de la ontología.
- [[scripts.audit_graph.py]] — 706 líneas · Auditoría automática del grafo (misión de reparación, G1).
- [[ontology.bulk_import.py]] — 682 líneas · ingesta masiva idempotente y validada (Wikidata/GLEIF).
- [[engine.maptime.js]] — 525 líneas · EL TIEMPO DENTRO DEL MAPA PRINCIPAL (2026-09-25) Fabrizio: "el grafo temporal y el normal deberían ser uno; el temporal no da mucho por sí solo". …
- [[scripts.migrate_v0_to_ontology.py]] — 503 líneas · Fase 1: migra data/grafo_v0.json (el snapshot congelado en Fase 0) a la ontología (Postgres, tabla events + vistas materializadas objects/links).
- [[ontology.bitemporal.py]] — 356 líneas · G(t, κ): el grafo vigente en la fecha t TAL COMO SE CONOCÍA en κ (INFRA_OPERATIVA §5.5).
- [[ontology.timeline.py]] — 334 líneas · Phase 1 · M5: la línea de tiempo de una entidad.
- [[ontology.vocabulary.py]] — 315 líneas · REGISTRO ÚNICO del vocabulario del grafo.
- [[scripts.import_companies.py]] — 311 líneas · terminal del importador de fichas khipus.company/1 (EXPANSION_5K E2.4).
- [[ontology.provenance.py]] — 285 líneas · Phase 1 · M1: procedencia de primera clase.
- [[ontology.db.py]] — 276 líneas · conexión a Postgres (fuente única de verdad de la ontología).
- [[engine.hypergraph.js]] — 273 líneas · Hipergrafos temporales agénticos para Khipu Finance Una hiper-arista conecta MÚLTIPLES nodos a la vez (un evento que afecta a N empresas) y tiene …
- [[engine.reconcile.js]] — 257 líneas · G3 (misión de reparación 2026-10-04) 🩺 Diagnóstico → "Grafo: base vs catálogo". Muestra el dry-run de ontology/reconcile.py (GET …
- [[ontology.vocabulary.json]] — 256 líneas · REGISTRO ÚNICO del vocabulario del grafo. Añadir un tipo de objeto, un tipo de relación o un sector se hace AQUÍ (dato), no editando código en 29 …
- [[engine.timeline3d.js]] — 254 líneas · El Grafo Temporal en 3D, donde la PROFUNDIDAD ES EL TIEMPO.
- [[ontology.ledger_models.py]] — 248 líneas · el LIBRO DE DECISIONES (docs/INFRA_OPERATIVA.md §2.1; paso 6 del plan).
- [[engine.secondbrain.js]] — 241 líneas · Second Brain de 5 capas para Khipu Finance Al seleccionar una empresa, abre un panel con 5 capas de conocimiento: 1. Mercado (precio + sparkline + …
- [[ontology.checkpoints.py]] — 212 líneas · PUNTOS DE CONTROL del grafo (docs/INFRA_OPERATIVA.md §5.5; paso 26).
- [[ontology.ingest_news.py]] — 205 líneas · Phase 1 · M4: las noticias entran al grafo.
- [[ontology.models.py]] — 201 líneas · esquema SQLAlchemy de la ontología.
- [[ontology.history_models.py]] — 125 líneas · LA MEMORIA DE LOS NÚMEROS (docs/BRECHAS_V2.md bloque 2: L3-01, L2-12, L3-14, L3-13).
- [[ontology.link_review.py]] — 112 líneas · COLA DE REVISIÓN de vínculos PROPUESTOS (2026-10-21, tras importar los lotes 2-4).
- [[scripts.reconcile_v0_to_ontology.py]] — 104 líneas · G3: reconciliar el catálogo (data/grafo_v0.json) con la ontología en Postgres SIN borrar nada.
- [[ontology.import_models.py]] — 94 líneas · tablas del importador de fichas khipus.company/1 (E2.3), APPEND-ONLY.
- [[ontology.governance_models.py]] — 62 líneas · REGISTRO DE GOBERNANZA (docs/INFRA_OPERATIVA.md §5.1; paso 9 del plan).
- [[scripts.link_origins.js]] — 56 líneas · ¿de qué arreglo del catálogo viene cada vínculo? (BRECHAS_V2 L3-11 / PROP-14, bloque 5: revisión de la escala de pesos.)
- [[ontology.sqltypes.py]] — 33 líneas · tipos SQL compartidos por los modelos del libro y de gobernanza (módulo HOJA: no importa ningún modelo; lo importan ontology/ledger_models.py y …
- [[ontology.__init__.py]] — 0 líneas

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| usa a | [[Capa Infraestructura]] | 48 |
| la usa | [[Capa Infraestructura]] | 40 |
| usa a | [[Capa Datos del catálogo]] | 34 |
| la usa | [[Capa Investigación]] | 15 |
| la usa | [[Capa Interfaz (Khipus OS)]] | 14 |
| la usa | [[Capa MCP y API]] | 13 |
| usa a | [[Capa Interfaz (Khipus OS)]] | 13 |
| la usa | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 12 |
| la usa | [[Capa Chat y agentes]] | 10 |
| la usa | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 9 |
| la usa | [[Capa Dinero (carteras, trading, corretaje)]] | 7 |
| la usa | [[Capa Comité]] | 6 |
| usa a | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 4 |
| usa a | [[Capa Investigación]] | 4 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 4 |
| la usa | [[Capa Otros]] | 3 |
| usa a | [[Capa Dinero (carteras, trading, corretaje)]] | 2 |
| la usa | [[Capa Voz]] | 1 |
| usa a | [[Capa MCP y API]] | 1 |
