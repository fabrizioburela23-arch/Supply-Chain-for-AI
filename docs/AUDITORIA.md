# AUDITORÍA — Fase 0 (previo a la Ontología)

Inventario del repo tal como estaba antes de construir la capa de ontología.
Generado leyendo el código real (no supuestos). Sirve de mapa para la Fase 1.

## Corrección de arquitectura vs. el roadmap original

El `ROADMAP_KHIPUS_ONTOLOGIA.md` que guía este trabajo fue escrito sin ver el
código y asume un stack que **no es el real**. Diferencias verificadas:

| Roadmap asume | Realidad verificada | Decisión |
|---|---|---|
| Backend Node.js | **Flask/Python** (`server.py`, 2916 líneas) | La ontología se implementa en Flask/SQLAlchemy, no se migra a Node. |
| Prisma / Zod / node-cron | Equivalentes Python: SQLAlchemy, Pydantic, APScheduler | Mismos conceptos, stack nativo. |
| `/api/v1/*` libre para la ontología | **`/v1/*` ya existe**: es un producto de API pública monetizado (Khipu Finance API, JWT por tiers `free/starter/pro/business/enterprise`, ver `khipu_auth()` en `server.py:2286`) | La API de ontología usa el prefijo **`/api/ontology/*`** para no colisionar. |
| "Postgres, no Neo4j" | **Neo4j Aura ya está conectado y en producción** (persistencia del Grafo Temporal, `NEO4J_URI/USER/PASSWORD`) | Se añade Postgres (Railway) como fuente de verdad de eventos/ontología. Neo4j se conserva como **espejo de solo lectura** para la vista de grafo temporal — no se apaga nada que ya funciona. |
| Vitest/Jest | El repo usa **pytest** (`tests/test_server_smoke.py`, 18 tests) | Los tests de la ontología se escriben en pytest. |
| Precios vía WebSocket propio | Ya existe `/api/quotes/live` (POST) + Finnhub/FMP/Marketstack/AlphaVantage como fallback en cascada | Se reusa tal cual; los precios entran a la ontología como eventos `PriceObserved`. |
| Alpaca no mencionado como ya integrado | **Ya integrado**: `/api/trade/*` (account, positions, orders, agent) usando `ALPACA_KEY/SECRET/BASE` | Se reusa; las órdenes se pueden vincular a `Decision` en Fase 2. |

## Dónde vive cada dato hoy (antes de la ontología)

| Dato | Dónde vive | Formato |
|---|---|---|
| Catálogo de empresas (463) | `app.html` (NODES core, líneas 2247-2971) + `nodes/nodes_expand{,2,3,4}.js`, `nodes/nodes_spacex.js`, `nodes/nodes_nuclear.js` | Arrays de objetos JS, mergeados por `id` en el cliente al cargar |
| Relaciones (1163) | `app.html` (RAW_LINKS core) + `nodes/links_{all,expand,connect}.js`, dentro de `nodes_nuclear.js` (LINKS_NUCLEAR) | Arrays `[s,t,w,rel,type]` o `{s,t,w,rel,type}`, normalizados vía `NODE_ID_ALIAS` |
| Categorías (40) | `app.html`: `CATS` + `CATS_NEW` (`Object.assign`) | Objeto id→{label,color,x} |
| Datos pre-IPO (14 empresas) | `nodes/preipo_intel.js` | Objeto id→{rounds, investors, milestones} |
| Hechos temporales (105, 86 aristas) | `nodes/temporal_seed_facts.js` + `temporal_seed_facts2.js` + `ontology_facts.js` | Array de hechos `{subject,predicate,object,valid_from,valid_until,rel,…}` |
| Ontología (8 tipos objeto, 12 tipos relación, 32 objetos no-empresa) | `nodes/ontology.js` | `window.ONTOLOGY = {types, rels, objects}` |
| **Portafolio del usuario** | **`localStorage` del navegador** (`MKT.pos`, clave `eco_pos`) | Cliente únicamente — **no vive en el servidor**. Se pierde al cambiar de navegador/dispositivo. |
| Cotizaciones cacheadas | `localStorage` (`eco_quotes`) + server-side cache (flask-caching, TTL) | Efímero |
| Persistencia del grafo temporal | Neo4j Aura (opcional; fallback a memoria nativa del servidor) | Grafo `(:Entity)-[:ASSERTS]->(:Fact)-[:ABOUT]->(:Entity)` |
| Second Brain (RAG) | Microservicio aparte `rag/` (ChromaDB + Flask), no desplegado aún | — |

## Problema concreto que motiva la ontología (evidencia real)

`SpaceX` en el catálogo actual: `{"ticker":"No cotiza · privada ~$350B (Musk)", "mkt": null, "preipo": true}`.
Esto es un **hardcode que no se actualiza solo** — SpaceX ya cotiza en la
realidad y el dato queda obsoleto sin que nada lo detecte. Es el caso de uso
canónico de la Fase 1 (bitemporal: un evento `ObjectUpdated` con
`valid_from` correcto reemplaza la edición manual de un array JS).

## APIs externas y desde dónde se llaman

Todas desde `server.py` (proxy centralizado, las keys nunca llegan al cliente
en modo servidor):

| Proveedor | Uso | Variable env |
|---|---|---|
| Finnhub | Cotizaciones, noticias | `FINNHUB_KEY` |
| FMP | Fundamentales, dossier, IPO calendar | `FMP_KEY` |
| Marketstack | EOD histórico | `MARKETSTACK_KEY` |
| Alpha Vantage | Fallback de cotizaciones/VaR | `AV_KEY` |
| GDELT | Noticias globales | (sin key) |
| SEC EDGAR | Fundamentales oficiales US | (sin key) |
| CelesTrak | TLE de satélites | (sin key) |
| Alpaca | Paper/live trading | `ALPACA_KEY/SECRET/BASE` |
| Anthropic (Claude) | Bixby, Canvas IA, análisis | `ANTHROPIC_KEY` |
| Gemini / NVIDIA NIM | Fallback multi-IA | `GEMINI_KEY` / `NVIDIA_KEY` |
| ElevenLabs | Voz conversacional (Bixby) | `ELEVENLABS_KEY/AGENT_ID` |
| Neo4j Aura | Persistencia grafo temporal | `NEO4J_URI/USER/PASSWORD` |
| MiroFish | Motor de simulación multi-agente | `MIROFISH_URL` |
| ChromaDB (RAG) | Second Brain | `RAG_URL` (no desplegado) |

## Tipos de objeto implícitos (para el esquema de la ontología)

- **Company**: 463 nodos, 40 categorías (`cat`) que mapean a "etapa de la
  cadena" (foundry, memory, quantum_hw, space_launch, nuclear_smr, …).
- **Objetos de ontología no-empresa** (ya modelados en `ontology.js`): `Tech`,
  `Policy`, `Country`, `Energy`, `Material`, `Product`, `Org` — 32 instancias.
- **Position**: implícito en `MKT.pos` (localStorage) — no es un objeto
  formal todavía.
- **Thesis/Annotation/Alert/Decision**: no existen — son 100% nuevos (Fase 2/4).

## Tipos de relación implícitos

De los datos crudos (`type`/`rel` en los links): `supply` (270), `cloud` (133),
`customer` (65), `partner` (40), `fab` (34), `license` (17), `owns` (9),
`invest` (3), `deploy` (1). De la ontología nueva (`ontology_facts.js`, 12
tipos semánticos): `fabrica, abastece, usa, invierte, sanciona, restringe,
controla, depende, energiza, alberga, compite, domina`.

## Tests y CI

- `tests/test_server_smoke.py`: 18 tests, sin necesitar API keys (smoke tests
  de rutas estáticas y respuestas). **Corregido en Fase 0**: un test afirmaba
  el nombre de marca antiguo ("Khipu Finance") tras el rebrand a "Khipus AI
  Finance Inteligence" — ahora solo valida que el campo exista.
- `security_audit.py`: auditoría estática de secretos + cabeceras de
  seguridad + arranque del server. No es parte de pytest; se corre aparte.

## Snapshot de migración

`scripts/export_graph_v0.js` (Node — solo herramienta de build, no vive en el
backend) replica la lógica exacta de merge/alias/filtro que corre en el
navegador (mismo orden de `<script src>`, mismo `NODE_ID_ALIAS`, mismo filtro
de `LINKS`) y produce `data/grafo_v0.json`.

Validado:
- 463 nodos con `id` único.
- 1163 links, el 100% resuelve a nodos existentes (grafo isomorfo, sin
  referencias colgantes).
- Coincide exactamente con los contadores que muestra la app en producción
  (463 empresas · 1163 conexiones · 40 categorías).

## Regla de oro para las fases siguientes

A partir de Fase 1, **el frontend deja de ser dueño del dato de dominio**.
`grafo_v0.json` es el snapshot de arranque de la ontología (Postgres); Neo4j
sigue siendo el motor visual del Grafo Temporal (lee de la ontología, no al
revés). Los datos que hoy están en `localStorage` (portafolio) migran a la
ontología en Fase 1/2 sin romper la experiencia actual mientras se hace el
switch.
