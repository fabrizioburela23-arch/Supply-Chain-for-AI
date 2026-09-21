# ARCHITECTURE — Khipus Finance AI → Live Investment Graph

Documento de decisión para **Phase 1 — Live Investment Graph V1**.
Escrito tras auditar el repositorio existente (~53.000 líneas) contra la
especificación. Fecha: 2026-09-21.

> **Regla que gobierna este documento:** la aplicación existe, está desplegada
> y funciona. La especificación dice explícitamente *"No destruyas
> funcionalidad existente innecesariamente"* y *"evita reorganizaciones
> innecesarias"*. Todo lo que sigue es **evolución aditiva**, no reescritura.

---

## 0. Advertencia sobre el estado de producción (2026-09-21)

Antes de leer nada más: **la instancia desplegada está degradada**. Diagnóstico
tomado del panel 🩺 del propio usuario el 2026-09-21:

| Subsistema | Estado | Causa |
|---|---|---|
| Postgres (ontología) | 🔴 caído | `postgres.railway.internal` no resuelve — el servicio no existe o se desvinculó |
| Neo4j Aura | 🔴 caído | el host no resuelve (instancia gratuita eliminada por inactividad) |
| Claude | 🔴 caído | saldo de la cuenta Anthropic agotado |
| Gemini / NVIDIA | 🔴 caídos | modelos retirados (`gemini-2.0-flash` → 404, `meta/llama-3.1-70b-instruct` → 410) |
| Finnhub | 🔴 429 | límite de llamadas |
| ElevenLabs, FMP/MarketStack/AlphaVantage | 🟢 vivos | — |

Consecuencia para Phase 1: **toda la capa de ontología está inoperativa en
producción hasta que se recree el Postgres**. El desarrollo y las pruebas de
esta fase se hacen contra Postgres local; el despliegue queda condicionado a
ese paso manual (documentado en `docs/ESTADO.md`).

**No se pudo inspeccionar la aplicación desplegada** como pedía la
especificación: el entorno de desarrollo bloquea toda salida a internet
(el proxy responde 403 al CONNECT). La comparación local↔desplegado se hizo
por git (mismo commit, árbol limpio) y por el diagnóstico anterior.

---

## 1. Qué es hoy la aplicación

No es una app de supply chain con vistas bonitas. Es, ya hoy, **un grafo
económico temporal con un motor de propagación encima**:

- **949 nodos / 2.526 relaciones** en 13 macro-sectores (semiconductores, IA,
  espacio, nuclear, defensa, energía, materiales, macro/crédito, inmobiliario,
  logística…). Dirección canónica única: `source` PROVEE a `target`.
- **Ontología bitemporal en Postgres** (`ontology/`): tabla `events`
  append-only + `objects`/`links` materializados. Cada evento lleva
  `valid_from`/`valid_to` (cuándo es cierto **en el mundo**) y `recorded_at`
  (cuándo **lo supimos**).
- **Hipergrafo real** (`matrix/`): ~69 Factores sistémicos como hiperaristas
  N-arias (`Factor --affects--> {N empresas}` con coeficiente por miembro),
  que modulan la fragilidad del kernel de propagación.
- **Motor de matrices** (NumPy, denso y disperso): matrices por tipo de
  relación, radio espectral ρ(T), chokepoints, PageRank, propagación de shocks
  y bandas Monte Carlo (VaR/CVaR).
- **Escritura auditada**: 13 Acciones tipadas (Pydantic) con `actor`
  obligatorio; cola de aprobación humana (`ProposedAction`) para lo que
  proponen los agentes.

### Cómo se mapea contra la especificación

| § Spec | Requisito | Estado real | Evidencia |
|---|---|---|---|
| 1 | Modelo de entidades extensible | 🟢 **ya existe** | `ObjectRecord.type` es `String(40)`, no un enum de BD → tipo nuevo = editar `vocabulary.json`, sin DDL |
| 2 | Relaciones con validez/confianza/fuente | 🟡 parcial | `valid_from/valid_to` sí; `confidence` se guarda en sitios sueltos; `source` es una etiqueta de canal |
| 3 | Modelo temporal bitemporal | 🟢 **fortaleza central** | `valid_*` vs `recorded_at` ya separa "qué creía el grafo" de "qué sabemos ahora"; `GET /graph?as_of=` funciona |
| 4 | Hipergrafo | 🟢 **ya existe** | `Factor` + `affects` + `active_factors()` + `fragility()` en `matrix/engine.py` |
| 5 | **Procedencia** | 🔴 **hueco mayor** | ver §2 abajo |
| 6 | Ingesta event-driven | 🟡 parcial | agentes + bulk import + radar; sin bus de eventos; noticias **no se persisten** |
| 7 | Datos vivos + interfaces de proveedor | 🟡 parcial | `core/providers/` existe con 1 adapter (CoinGecko); **`base.py` se cita en el docstring pero no existe**; equities van directo a Finnhub/FMP |
| 8 | Resolución de entidades | 🔴 **hueco mayor** | ver §3 abajo |
| 9 | Elección de base de grafo | 🟢 **ya decidida** | ver §4 abajo |
| 10 | Event store | 🟢 **ya existe** | `events` append-only; el estado se deriva de eventos |
| 11 | Graph API | 🟡 parcial | existen objects/links/history/graph/diff; faltan `/search`, `/events/{id}`, timeline unificada |
| 12 | UI del grafo vivo | 🟡 parcial | búsqueda, ficha, grafo interactivo, línea de tiempo; **sin panel de procedencia** |
| 13 | Estado "LIVE" honesto | 🟢 mayormente | 🩺 diagnóstico en vivo + linaje ⓘ de precio con antigüedad |
| 14 | Calidad de dato | 🟡 parcial | `confidence` se almacena; solo se usa como umbral de auto-aprobación |
| 15 | Compatibilidad con agentes futuros | 🟢 **fortaleza** | el catálogo de Acciones ES la API de escritura para agentes; `ProposedAction` ES el human-in-the-loop |
| 16 | Escala | 🟡 límite conocido | 949 nodos hoy; `docs/ESTADO.md` marca rework del cliente antes de ~2.500 |
| 17 | Seguridad | 🟢 mayormente | keys solo en el server, `rate_limit` en `core/http.py`, JWT en `/v1/*`, PIN de trading, auditoría vía `ActionExecuted` |
| 18 | Estructura de repo | ⚠️ ver §5 | recomendación: **no reorganizar** |
| 19 | Documentación | 🟡 este documento la inicia | — |
| 20 | Restricciones (no trading auto) | ⚠️ nota | el trading **en papel** ya existe (Alpaca + PIN). No se amplía en Phase 1 |

**Conclusión de la auditoría:** entre el 60 % y el 70 % de Phase 1 ya está
construido. Lo que falta no es un sistema nuevo — son **tres capas concretas**
sobre la espina dorsal que ya existe.

---

## 2. Hueco mayor #1 — Procedencia (spec §5)

La especificación es tajante: *"NINGÚN hecho importante debe existir sin poder
conocer su origen"*, y exige navegar `Graph Claim → Source → Original evidence`.

**Hoy eso no es posible.** Lo que hay:

- `Event.source` es `String(60)` y contiene un **canal**, nunca un documento:
  `'manual'`, `'radar'`, `'tejedor'`, `'migration_v0'`, `'gdelt'`.
- **No existe ninguna tabla ni entidad** `Source` / `Document` / `Evidence`.
- Pero `ontology/vocabulary.json` **ya declara** los tipos de objeto `Source`
  y `NewsItem` (líneas 22-23) y un `source_kinds` con niveles de confianza
  (`primary: trust 3`, `press/trade: 2`, `rumor/aggregator/corporate/state: 1`)
  descrito como *"base del filtro de OBJETIVIDAD"*. **Ningún código los lee ni
  los crea.** Es un vocabulario sin motor.
- El **único** sitio con URLs estructuradas es `CrearTesis.fuentes`
  (`FuenteCitada{url, titulo, publicador, fecha, cita_textual, consultado_at}`),
  que produce el agente Investigador. Se entierra en `Thesis.properties` y
  **ni siquiera aparece en el evento `ActionExecuted`** que deja el rastro
  auditable.
- La evidencia solo es clicable mientras la propuesta está pendiente. **Al
  aprobarla, desaparece de todas las vistas.**
- El resumen de una noticia GDELT se guarda como texto (`[GDELT] …`) y **la URL
  del artículo se descarta**.

También se detectó un **defecto real**: los campos `fuente` de varias Acciones
admiten hasta 200 caracteres y se vuelcan a `Event.source`, que es
`String(60)` → truncamiento o error en escritura.

---

## 3. Hueco mayor #2 — Identidad de entidad (spec §8)

- **Cuatro resolvedores divergentes**, con tablas de alias y umbrales
  distintos: `engine/resolve.js` (cliente, fuzzy + ~230 alias de voz),
  `core/semantic.py`, `ontology/agents.py:_resolve`,
  `scripts/ingest_enrichment_md.py`. Solo uno tiene umbral (60), hardcodeado
  en un único consumidor.
- **`NODE_ID_ALIAS` muere en la frontera cliente→servidor**: vive en
  `nodes/nodes_seed.js`, el exportador lo usa como *entrada* pero **no lo
  incluye en `data/grafo_v0.json`** — por eso la migración nunca lo ve, y por
  eso **la base de producción conserva los duplicados** que el cliente resuelve
  en memoria.
- **No hay `canonical_entity_id`, ni `aliases[]`, ni `external_ids{}`.**
  `ticker`/`mkt` caen en el JSONB por un barrido genérico, sin índice ni
  unicidad. CIK se resuelve ad-hoc contra SEC y **no se persiste**. ISIN y LEI
  no existen.
- **La resolución no se registra**: el score y el método se calculan y se
  tiran. Imposible auditar por qué un texto acabó en una entidad.

Además, un hueco transversal de seguridad de datos: **`apply_event()` — la
puerta principal de escritura — no valida `type` ni `rel_type`** contra el
vocabulario. Prueba viva: `justified_by` está persistido en la base y no
existe en `vocabulary.json`; el motor de matrices lo descarta en silencio.

---

## 4. Decisión: base de datos del grafo (spec §9)

**Decisión: seguir en PostgreSQL. No introducir Neo4j como fuente de verdad,
ni Apache AGE, ni una base de grafo nueva.**

Razones, en orden de peso:

1. **El modelo temporal ya vive aquí y es lo más difícil de replicar.** La
   bitemporalidad (`valid_*` + `recorded_at`) sobre una tabla append-only es
   exactamente lo que pide la spec §3, y está probada.
2. **Los recorridos que necesitamos no son de grafo profundo.** La propagación
   de shocks se hace con **álgebra matricial en NumPy** sobre matrices dispersas
   por tipo de relación, no con traversals. Para eso Postgres es un almacén
   perfectamente adecuado, y las matrices se cachean por época del grafo.
3. **Escala.** 949 nodos / ~3.000 aristas. Postgres con los índices actuales
   sirve esto holgadamente, y llega a 10⁵-10⁶ aristas sin cambiar de motor.
   La spec dice explícitamente: *"No optimizar prematuramente para 10M nodos"*.
4. **Coste y operación.** La instancia gratuita de Neo4j Aura **se borró sola
   por inactividad** durante 7 semanas — evidencia directa de que añadir un
   almacén de estado más es añadir una cosa más que se cae.
5. **Riesgo de migración.** Mover la fuente de verdad implicaría reescribir
   `ontology/service.py`, `matrix/engine.py` y las 13 Acciones. La spec pide
   evitar exactamente eso.

**Neo4j se mantiene donde está hoy: espejo visual opcional de solo lectura.**
Si se cae, la app sigue en modo nativo (patrón `*_available()`).

**Cuándo reabrir esta decisión:** si aparecen consultas de camino variable de
verdad (p.ej. *"toda cadena de suministro de ≤5 saltos entre A y B, filtrada
por país"*) que la representación matricial no exprese bien. Hasta entonces,
`pgvector` para búsqueda semántica y particionado temporal de `events` cubren
el crecimiento previsible.

---

## 5. Decisión: estructura del repositorio (spec §18)

La spec propone `/apps/{web,api}`, `/services/*`, `/packages/*` y menciona
TypeScript/React.

**Decisión: NO reorganizar, y NO reescribir la UI a React.**

- La separación que pide la spec **ya existe, con otros nombres**:
  `core/` = `packages/shared` + `packages/providers`; `ontology/` + `matrix/` =
  `packages/domain` + `services/graph`; `server.py` = `apps/api`;
  `app.html` + `engine/` = `apps/web`.
- Reescribir la UI (10.173 líneas de `app.html` + 30.000 de `engine/*.js`) a
  React sería **destruir meses de trabajo funcional** para obtener la misma
  funcionalidad. La spec lo prohíbe salvo justificación, y aquí no la hay.
- El archivo único `app.html` **sí es una deuda real** (bloques `<script>`
  inline, sin bundler). Se aborda incrementalmente extrayendo a `engine/*.js`,
  que es el camino que el proyecto ya sigue desde hace meses.

Lo que **sí** se hace: cuando un módulo nuevo tiene sitio natural en
`core/providers/` o en un paquete propio, se crea ahí — no dentro de
`server.py`.

---

## 6. Arquitectura objetivo de Phase 1

```
  FUENTES              INGESTA            GRAFO                 CONSUMO
  ───────              ───────            ─────                 ───────
  Finnhub  ─┐                          ┌─ events (append-only) ─┐
  FMP       ├─ core/providers/ ──┐     │    ↓ materializa       ├─ /api/ontology/*
  CoinGecko │   (adapters con    ├──►  ├─ objects / links       ├─ /api/matrix/*
  GDELT     │    esquema común)  │     │    ↓ deriva            ├─ UI (app.html +
  SEC       ─┘                   │     └─ matrices (NumPy)      │   engine/*.js)
                                 │                              └─ agentes (Fase 2)
                    resolución ──┤
                    de entidad   │     PROCEDENCIA transversal:
                                 └──►  cada evento → Source (url, kind, trust,
                                       published_at, retrieved_at)
```

Las tres capas que faltan, en orden de dependencia:

1. **Procedencia** — todo lo demás la referencia. Sin ella, los agentes de
   Fase 2 no pueden razonar sobre calidad de evidencia (spec §14, §15).
2. **Identidad de entidad** — para que la ingesta automática sepa a qué
   entidad pegar un hecho sin duplicar.
3. **Proveedores + ingesta de eventos** — para que noticias y filings entren
   al event store como hechos con fuente, en vez de ser un passthrough.

El orden importa: ingerir noticias **antes** de tener procedencia e identidad
llenaría el grafo de hechos sin origen y de entidades duplicadas.

---

## 7. Qué se reutiliza, qué se modifica, qué es nuevo

| | Componentes |
|---|---|
| **Se reutiliza tal cual** | event store bitemporal, `objects`/`links`, motor de matrices, hiperaristas/Factores, catálogo de 13 Acciones, cola `ProposedAction`, `rate_limit`, diagnóstico 🩺, toda la UI existente (mapa, terminal, X-Ray, Grafo Temporal, Guía) |
| **Se modifica (aditivo)** | `Event` gana `source_id` y `confidence`; `apply_event()` acepta procedencia; `crear_tesis` registra sus fuentes como entidades; `vocabulary.json` gana `evidenced_by`; el Registro de Acciones muestra las fuentes |
| **Nuevo** | `ontology/provenance.py`; entidades `Source`; endpoints de procedencia; (M2) identidad canónica; (M3) `core/providers/base.py` |
| **Explícitamente fuera de Phase 1** | broker execution, trading automático, recomendaciones, optimización de cartera, MCP, enjambre de agentes |

---

## 8. Cómo levantar el sistema localmente

```bash
# 1. Dependencias
pip install -r requirements.txt

# 2. Postgres local (la ontología es opcional: sin DATABASE_URL la app
#    arranca igual, pero /api/ontology/* y /api/matrix/* devuelven 503)
service postgresql start
createdb khipus_test

# 3. Poblar la ontología desde el repo (949 empresas + 69 factores + 28 asientos)
DATABASE_URL=postgresql://postgres:devpass@localhost:5432/khipus_test \
  python3 scripts/migrate_v0_to_ontology.py --reset

# 4. Tests (los de ontología se auto-saltan sin DATABASE_URL)
DATABASE_URL=postgresql://postgres:devpass@localhost:5432/khipus_test \
  python3 -m pytest tests/ -q

# 5. Servidor
SECRET_KEY=dev python3 server.py
```

Variables de entorno: ver `CLAUDE.md` § "Variables de entorno" y `.env.example`.
**Ninguna key va nunca al navegador**: el servidor actúa de proxy de todas.

---

## 9. Qué fuentes están REALMENTE activas

Honestidad explícita, como pide la spec (*"No declares una integración como
'live' si utiliza datos falsos"*):

| Fuente | Estado | Nota |
|---|---|---|
| FMP, MarketStack, AlphaVantage | 🟢 activas | respaldo de precios; verificadas en el 🩺 del usuario |
| CoinGecko | 🟢 activa | único adapter que pasa por `core/providers/` |
| Finnhub | 🟡 con key, hoy 429 | precios primarios |
| GDELT | 🟡 se consulta, **no se persiste** | passthrough al cliente; la URL se descarta |
| SEC EDGAR | 🟡 solo ticker→CIK ad-hoc | no se persiste en ninguna entidad |
| Claude / Gemini / NVIDIA | 🔴 caídas hoy | saldo agotado / modelos retirados |
| Alpaca | 🟢 papel, con PIN | fuera del alcance de Phase 1 |

Ninguna parte del sistema inventa datos de mercado. Cuando una fuente no
responde, la UI lo dice (🩺, badges de estado, linaje ⓘ con antigüedad).
