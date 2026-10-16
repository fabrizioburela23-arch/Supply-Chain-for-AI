# Khipus Finance Intelligence — CLAUDE.md

Terminal financiero (estilo Bloomberg + ontología estilo Palantir) para la
cadena de suministro de IA + capas macro. 937 nodos en el catálogo (la base de
producción tiene 1.294 objetos), 2.510 relaciones (dirección ÚNICA: source PROVEE
a target; 9 tipos de relación; 13 macro-sectores en SECTORS9 — expansión
multicapa 2026-08-02: energía, materiales, macro_credito, inmobiliario,
logistica). ~70 Factores sistémicos LATENTES (severity 1.0) con
`severity_crisis` en props — se disparan como what-if vía
`POST /api/matrix/factor/fire`, nunca dejarlos todos en severidad de crisis
(satura: ρ 2.63). Tope FRAGILITY_CAP=2.5 por nodo (artefacto `kernel.params` de governance/, leído por matrix/engine.py).
Desplegado en Railway (push a `main` auto-deploya, ~2 min).

**Al iniciar una sesión de trabajo: lee SOLO la sección «▶ PRÓXIMA SESIÓN» de `docs/ESTADO.md`** (el resto es historial: grep) — es la memoria
entre sesiones (qué se construyó, decisiones tomadas, qué falta).
`docs/AUDITORIA.md` = inventario de dónde vive cada dato.
**Arquitectura objetivo: `docs/ARQUITECTURA_V2.md`** (2026-10-11) — grafo = identidad/relaciones, vectores = estado,
tensores = solo cálculo derivado y versionado; Postgres como única base (sin base de grafos ni vectorial aparte);
un solo kernel, un solo NRS, un solo motor de contexto ($R(v\mid Q)$ + presupuesto). Antes de construir algo
"avanzado", ver su sección 19 (qué NO hacer) y la Fase 1 (20.1, orden de implementación).
**Brechas verificadas: `docs/BRECHAS_V2.md`** (2026-10-12) — 99 hallazgos medidos en el código contra la v2 (4 críticos:
7 motores de contagio con 164-315 empresas para el mismo choque, guardián de cifras que deja pasar "233,95 USD" y ±15 %,
sin historia de precios/FX/posiciones, ordenes por 3 caminos con controles distintos), lo que necesita decidir
Fabrizio (sección 2) y el orden de trabajo (bloques 0-5, sección 3). Empezar por ahí antes de la Fase 1.
**Infraestructura operativa: `docs/INFRA_OPERATIVA.md`** (2026-10-12) — los 4 pilares pedidos por Fabrizio: Objetos de
Decisión (libro mayor append-only con cadena de hashes, `core/decisions.py`), Puertas SHACL (TTL versionados compilados a
validadores Python de 0,01-0,3 ms; pySHACL solo como oráculo en CI), Hot Path Views (vistas en memoria versionadas por
`graph_version` tomado al confirmar, `/api/hot/*`, UN kernel) y Gobernanza (artefactos con hash, release aprobado con PIN,
G(t,κ) y replay). Plan de 26 pasos desplegables en su §10; decisiones nuevas D1-D7.
**CIERRE (2026-10-13): los 26 pasos están hechos** — `docs/CIERRE_INFRA.md` (español simple) dice qué hace cada pilar,
el estado de los 99 hallazgos de BRECHAS con su prueba, las 10 rutas de escritura que aún no dejan decisión (fijadas en
tests/test_cierre_infra.py: la lista solo puede ACHICARSE) y los clics exactos que solo Fabrizio puede hacer (ratificar,
activar kernel 2.0.0 / shapes / gates / guard con PIN, Railway). Empezar por ahí antes de la "Fase 2+".
**Lo construido, lote por lote (detalle en `docs/CLAUDE_DETALLE.md` §1 — leer la parte que toque antes de cambiarla):**
- Infra operativa (pasos 1-26, 2026-10-13): libro de decisiones append-only con cadena de hashes (`core/decisions.py`,
  `core/ledger.py`), identidad (`core/identity.principal()`), vistas rápidas `/api/hot/*` (`core/hotviews/`, UN kernel),
  gobernanza con artefactos y PIN (`governance/`, `core/governance*.py`), puertas SHACL compiladas (`core/gates/`), G(t,κ)
  (`ontology/bitemporal.py`), replay (`core/replay.py`), guardia del libro (`core/ledger_guard.py`). Toda escritura deja
  UNA decisión; sin libro → 503. Nunca activar versiones `activation: pin` por mi cuenta.
- UN camino de órdenes: solo `brokerage/alpaca.py` habla con /v2/orders|positions; todo pasa por `brokerage.service`.
- Historia de precios (`core/prices_store.py`), riesgo (`core/risk_models.py`), escenario → dinero (`core/scenario_pnl.py`).
- Chat con interfaz generativa (`core/genui/`, `engine/genui*.js`, GENUI off|shadow|on + bandera `kh_genui`).
- Escala a 5.000 (lote J), importador de empresas + países ISO-2 + categorías (lote K), 386 empresas + panel 📥 Importar +
  mapa con empresas de la base + precios del universo (lote L). Plan y pendientes: `docs/expansion/EXPANSION_5K.md`.
- UNA cartera: `engine/pfstore.js` (`MKT.pos` = vista de la cartera activa; `eco_pos` solo copia).
## Arquitectura

- **BÓVEDA OBSIDIAN + GRAFO DEL CÓDIGO (2026-10-11)**: `vault/` es el repo visto como bóveda de Obsidian
  (una nota por módulo, grupo de API → módulo → quién la llama, herramienta MCP, variable de entorno —SOLO
  nombres— y sesión de este ESTADO; capas con colores; `01 Reporte del grafo` = cosas sueltas: sin pruebas,
  globales/rutas sin uso, variables sin documentar) + `vault/_grafo/graph.json` y `mapa.html` (mapa
  interactivo, d3 de cdnjs). La genera `python scripts/build_vault.py` (determinista, stdlib, sin IA ni red;
  la tabla de capas `REGLAS_CAPA` vive ahí). REGLA: regenerarla antes de commitear cambios que agreguen/quiten/
  renombren módulos, endpoints o variables de entorno — y como `tests/test_vault.py` corre `--check` (bóveda
  vieja = suite roja), en la práctica antes de todo commit que toque código o docs. Conflicto de merge dentro de
  `vault/` → NO resolver a mano: quedarse con cualquiera de los dos lados y regenerar. No editar notas generadas;
  lo personal va en `vault/Mis notas/` (el generador no la toca); `.obsidian/app.json`/`graph.json` se crean si
  faltan y después son de Fabrizio (solo se refrescan los colores de capa). `vault` está en .dockerignore.
- `app.html` (~3,460 líneas): el HTML/CSS de TODA la UI, 4 bloques `<script>`
  inline + su JS propio en `engine/app_*.js` (G5-06, 2026-10-13: PARTIDO SIN CAMBIAR COMPORTAMIENTO — cada archivo
  es, byte a byte, un bloque inline de antes, cargado con `<script src="engine/app_X.js"></script>` EXACTAMENTE donde
  estaba; scripts clásicos que comparten el ámbito global como antes, NUNCA defer/async/module). Orden:
  `app_main.js` (núcleo: i18n, tema, NRS, mapa d3, pestañas, precios, 🩺, arranque) → … → `app_coordinator.js`
  (Coordinator + Análisis/Terminal/Simulación) → `app_trade_panel.js` → `app_preflight.js` → `app_canvas.js` →
  `app_scatter.js` (lista fija en tests/test_app_split.py). Siguen INLINE a propósito: el 1.º bloque (arranque de
  emergencia + seguridad compartida + franja "servidor no disponible": debe correr aunque falle un archivo externo),
  el orbe (diminuto), el vigía de /api/health (red de seguridad del servidor caído) y la insignia de 👥 Clientes
  (diminuta); el CSS sigue inline (/engine se sirve como JS y el ?v= solo versiona .js). Código nuevo de app.html
  va al engine/app_*.js que corresponda, NUNCA a un bloque inline nuevo. Las pruebas leen el texto de antes con
  `tests/_app_source.app_source()` (vuelve a poner cada archivo en su `<script>`); solo las del orden de carga,
  el SHELL de sw.js y la cuenta de bloques leen app.html crudo. Esos archivos van con ?v=N INMUTABLES (antes iban en
  el HTML, siempre fresco): editarlos = subir CACHE de sw.js Y añadir una entrada a `tests/app_js_fingerprint.json`
  (la prueba imprime las huellas; sin las dos cosas la suite falla). Un shell guardado sin copia de sus app_*.js no
  se sirve offline (sw.js `shellCanBoot` → página offline). Tabs: map, market, analysis, geo, simulation, space, terminal,
  canvas, crypto, portfolios, tkg (◈ Grafo Temporal — ya SIN botón de pestaña: se abre como vista
  desde ⏱ del mapa, engine/maptime.js), guia (❓ Guía). La MISMA lista vive en core/khipu_chat.TABS
  (lo que el chat puede abrir; tests/test_cleanup_server.py las compara).
- `server.py` (~5,800 líneas): Flask sync + gunicorn **1 worker + GUNICORN_THREADS (12)**, `exec` + `--graceful-timeout 25`
  (NO subir workers: el estado en memoria — caché, rate limits, agente de
  trading — divergiría entre workers). Proxy de todas las APIs externas.
- `core/` (paquete Python): helpers compartidos server/ontology/matrix —
  `config.py` (keys IA/Finnhub/timeout), `http.py` (_safe_get/_safe_ticker +
  `rate_limit`, el decorador que usan server/matrix/ontology),
  `ai.py` (cascada Claude→Gemini→NVIDIA + _extract_json), `quotes.py`
  (_fetch_quote_raw), `entities.py` (Phase 1 M2: EL resolvedor server-side —
  id/ticker/label/alias/sufijo, devuelve {id,score,method,matched}; dos
  umbrales: ESCRITURA 85 vs BÚSQUEDA 60). Rompe la circularidad ontology→server.
  `company_data.py` (estados anuales FMP→Yahoo→AV en USD y perfil EN VIVO
  Yahoo/Finnhub; lo usan /api/findossier, /api/dossier y /api/company/live —
  NUNCA inventar cifras: el viejo `_dossierSynthetic` con Math.random se borró).
- `matrix/` (paquete Python, opcional): motor de matrices — `engine.py`
  (build_matrices por rel_type + as_of, active_factors=hiperaristas,
  fragility, propagate=EL kernel de shocks, compute_metrics/chokepoints),
  `api.py` (blueprint /api/matrix/*: status, /<rel_type>, POST /impact,
  /metrics, POST /insights, GET /insights/history, POST /factor/fire).
  Convención A[i,j]=i PROVEE a j. Sin DATABASE_URL → 503. `SOLE_LINK_FLOOR=6` (2026-10-06): la
  columna de cada tipo se normaliza por max(suma, 6) — un proveedor único transmite según su peso.
  Los números del kernel viven en `governance/artifacts/kernel.params@*.json` (paso 9); el navegador
  NO propaga (paso 13): lee /api/hot/* con engine/hotclient.js.
  `tensor.py` + `tensor_api.py` (ONTOLOGÍA NIVEL 2, 2026-10-06, sin BD): tensor de flujo R×N×N,
  influencia Ψ (misma semántica que propagate), métricas por empresa (concentración, países de
  proveedores, cap. aguas abajo en riesgo, fuentes de riesgo, comparables) y `suggest_links` para
  empresas nuevas (IncorporarEmpresa las PROPONE con confidence 0 → revisión). /api/tensor/*.
- `ontology/` (paquete Python): ontología Palantir-style —
  `models.py` (events bitemporal + objects/links materializados +
  ProposedAction + Alert + InsightSnapshot), `provenance.py` (Phase 1 M1:
  Source como ENTIDAD, id derivado de la URL, trust del vocabulario),
  `service.py` (apply_event con source_id/confidence, as_of_graph, diff_graph),
  `actions.py` (catálogo de 17 Acciones auditadas, Pydantic — incluye
  Activar/DesactivarFactor, RetractarVinculo, FusionarEntidad), `agents.py`
  (7 agentes + brief matinal + evaluador de alertas), `api.py` (blueprint).
- `engine/`: módulos del navegador. **Khipus OS** (`docs/KHIPUS_OS.md`) es LA interfaz: Cabina (cockpit.js) +
  Escritorio de ventanas (desktop.js, `BixbyCockpit.stage` → `KhipuDesk.open`) + ventanas nativas (oswindows.js) +
  mascotas (mascot.js). El navegador NO propaga: lee `/api/hot/*` con `engine/hotclient.js`. Detalle de cada módulo
  (temporal-graph, maptime, globe, universe2d, xray, livesim, insights, brief…): `docs/CLAUDE_DETALLE.md` §2.
- `nodes/`: catálogo de empresas (nodes_*.js) + links (links_*.js) +
  ontology.js/ontology_facts.js (tipos y hechos tipados) +
  temporal_seed_facts*.js (105 hechos con fechas reales) + preipo_intel.js +
  legal_names.js (nombres legales → id; la usan resolve.js Y core/entities.py
  vía el snapshot — tras editarla, regenerar data/grafo_v0.json) +
  listing_status.js (GENERADO: estado en bolsa verificado con fuente — IPOs,
  compras, quiebras — que pisa al catálogo en merge_graph.js; regenerar con
  scripts/build_listing_status.py + export; nunca editar a mano).
- `scripts/`: export_graph_v0.js (snapshot) · migrate_v0_to_ontology.py.
- `data/grafo_v0.json`: snapshot canónico (937 nodos / 2.510 links + la tabla
  `node_id_alias`, que antes NO se exportaba y por eso el servidor no podía
  resolver alias) — se regenera con `node scripts/export_graph_v0.js` (usa nodes/merge_graph.js,
  la MISMA implementación de merge que el navegador; nunca duplicar).
- `research/` (Phase 2 — Agent Research Swarm): 8 agentes producen CLAIMS
  con evidencia citada (E#), horizonte, confianza CALCULADA y falsadores;
  tablas research_claims/research_evidence/claim_relations/agent_runs/
  research_jobs; blueprint `/api/research/*` (jobs, entity, claims/<id> =
  ¿Por qué?, activity, agents, budget, events). UI: engine/research.js
  (`window.KhipuResearch.open(id)`), comando `<TICKER> RESEARCH`. NUNCA
  COMPRA/VENTA. Env: RESEARCH_MODEL_DEFAULT / RESEARCH_MODEL_<TIPO>,
  RESEARCH_DAILY_BUDGET_USD (2.0), RESEARCH_AUTO_EVENTS (off). Docs:
  AGENT_ARCHITECTURE, CLAIM_MODEL, MODEL_ROUTING, AGENT_SECURITY.
- **Phase 3 y siguientes** (comité, corretaje multi-cliente, MCP, World/Space Monitor, gasto de IA, Jev, misión de
  reparación, chat Khipu, voz, habilidades por agente, limpieza «sin cosas sueltas»): `docs/CLAUDE_DETALLE.md` §3 +
  docs/PHASE3.md, BROKERAGE.md, MCP.md, JEV.md. Reglas que NO se pueden olvidar: gasto de IA solo por `core/ai.py`
  (`ai_context`); reloj único `core/scheduler.py`; registro único de agentes `engine/agents_registry.js`; diálogos solo
  con `KhipuToast`; PIN solo por `core/pin.py` / `window._tradeFetch`; consumidores de jobs tratan `partial` y
  `deferred`; columnas nuevas en `ontology/db._COLUMNAS_TARDIAS`; chat = solo lectura, nunca órdenes.
- `sim/`: scenario_builder.js (seeds de escenario; `buildScenarioSeed`).
- ELIMINADOS (no recrear): `rag/` (nunca desplegado), `litellm/`,
  `nodes/nodes_core.js` (duplicado), el modo standalone y el stack de keys en
  el navegador (2026-07); `engine/geoglobe.js`, `engine/planetarium.js` y
  `sim/mirofish_client.js` + todo el proxy/diagnóstico de MiroFish (2026-09:
  era un microservicio EXTERNO; lo reemplazan los motores internos
  core/sim_agents.py y matrix/engine.py).

## Una base de datos: Postgres

- **Postgres** (`DATABASE_URL`, plugin de Railway): FUENTE ÚNICA DE VERDAD de
  la ontología. Eventos inmutables con `valid_from/valid_to` (validez) +
  `recorded_at` (sistema). Time-travel: `GET /api/ontology/graph?as_of=`.
  El Grafo Temporal es NATIVO (cliente + esta base; `/api/grafo/estado` → `store: 'native'`).
- **Neo4j se RETIRÓ el 2026-10-13** (decisión #6 de Fabrizio, docs/BRECHAS_V2.md): nadie lo leía. NO
  reintroducirlo (ni driver, ni `NEO4J_*`, ni `/api/grafo/seed`; tests/test_neo4j_retirado.py lo vigila).
- OPCIONAL: sin `DATABASE_URL` el server arranca igual (patrón
  try/except + `*_available()`). Nunca romper ese patrón.

## Namespaces de API — CRÍTICO

- `/api/*` — endpoints internos de la app.
- `/api/ontology/*` — ontología (objects, graph, actions, agents, alerts).
- `/v1/*` — **API pública MONETIZADA por tiers (JWT, `khipu_auth`). NO tocar,
  NO usar para features internas.**
- `/mcp` (+ `/oauth/*`, `/.well-known/*`) — servidor MCP para IAs externas
  (tokens kmcp_ propios, NO los JWT de /v1). `/api/brokerage/*`,
  `/api/committee/*`, `/api/world/*` — Phase 3.
- **DINERO — regla de oro**: toda orden de clientes pasa por
  `brokerage.service.preview_order → confirm_order/approve_preview`. Lo que
  proponen `mcp` o `committee` SIEMPRE espera aprobación humana (PIN) salvo
  BROKERAGE_AUTO_APPROVE_PAPER=on en cuentas de papel. Nunca crear otro camino
  que envíe órdenes a Alpaca: desde el paso 15 también el panel, la voz, cripto, la terminal, el cierre y el
  agente de trading van por `brokerage.service` (house_order/house_close) y SOLO brokerage/alpaca.py habla con
  /v2/orders|positions (un test lo escanea).

## Convenciones de datos críticas

- `computeNRS(nodeId)` → NUMBER 0-100, NO objeto. Memoizado (`_nrsCache`);
  llamar `window._invalidateNRS()` si LINKS cambia. **UNA fórmula (limpieza 2026-10-11)**: cliente =
  `_nrsTerms` (engine/app_main.js; computeNRS y computeNRSBreakdown la usan; secondbrain.js lee el desglose);
  Python = `core/world.client_nrs` (servidor `_compute_server_nrs`, MCP y `portfolio_ai.nrs` delegan ahí,
  con el grado de la ontología o del catálogo). Margen acotado [0,20] en las dos; redondeo como JS.
  tests/test_cleanup_nrs_parity.py corre la del navegador sobre TODO el catálogo y exige el mismo número
  que Python. Nunca re-escribir la fórmula en otro archivo. **El grado es ESTRUCTURAL (G4d, 2026-10-04)**: cuenta
  pares distintos source→target unidos por una relación de FLUJO
  (`vocabulary.json` `flow: true`: supply/fab/cloud/license/ppa/owns/deploy);
  partner/invest/affects/about y los pares duplicados NO cuentan. Misma regla
  en cliente (`_buildNrsDegree`, lista `NRS_FLOW_TYPES`), servidor
  (`server_flow_degree`, COUNT DISTINCT en SQL), catálogo
  (`ontology.vocabulary.flow_degree`: MCP `_nrs` y core/world). Consecuencia:
  los NRS visibles BAJAN para empresas con muchos socios/accionistas (el término
  "cadena" ya no se infla con 753 partner + 192 invest + 48 pares repetidos).
- **Confianza por link (G4c)**: `LINKS[i].conf` (0-1) y `.verified` salen del
  merge (`linkTrust` en nodes/merge_graph.js: texto "no verificado/no revisado/
  posible/sin confirmar" → 0.3/false; un 6.º elemento `{conf, verified, since}`
  en la fila del catálogo manda). El snapshot los exporta; `matrix/engine.py
  _eff_weight` multiplica el peso por conf (el navegador ya no propaga, paso 13); el MCP
  (`_link_trust`) los deriva del texto si el snapshot aún no los trae.
- **Proveedor/cliente = solo FLUJO (G4a)**: `get_company.top_suppliers/
  top_customers` y `get_supply_chain.edges` excluyen partner/invest (van en
  `related`; `include_partners: true` los devuelve a `edges`). Cada arista lleva
  `relation_class` (mapa cerrado en mcp_server/tools.py RELATION_CLASS).
- **Fecha centinela (G4b)**: `valid_from` = 2000-01-01 es `GENESIS_SENTINEL`
  (ontology/service.py, `is_genesis`): "desde que se rastrea", NO una fecha
  real. API/timeline/MCP la marcan `valid_from_known: false`; la UI muestra
  "desde que se rastrea / since tracked". Al serializar un valid_from nuevo,
  marcarlo igual.
- `RAW_LINKS`: arrays `[s, t, w, rel, type]`; los `{s,t,type}` de
  links_expand.js se convierten en el merge; `NODE_ID_ALIAS` normaliza ids.
- `LINKS` (post-merge): objetos `{source, target, w, rel, type}` — usar
  `lid(l.source)` para el id.
- `MKT.quotes[ticker] = {close, prev, pct?, live?, src, as_of, currency?, converted?}`
  (contrato 2026-10-04): `live` es el precio NUMÉRICO o está AUSENTE — NUNCA un
  booleano (LivePrices escribía `live:true` y `parseFloat(q.live)` daba NaN → "—" en
  la Terminal y precio 0 al operar). `src` ∈ finnhub|yahoo|marketstack (+ `via:'live_caps'`)
  y `as_of` (ISO) dicen fuente y antigüedad. Leer el precio SIEMPRE con
  `window.quotePx(q)`; chip de fuente `quoteSrcChip(q, ticker)`; "en vivo" = `quoteIsLive(q)`.
  NO usar `q.c` ni `q.pc`. Los precios de TODO el catálogo (569 tickers, todas las
  bolsas) llegan por `window.loadLiveQuotes()` (lotes de 100 → POST /api/quotes/live →
  `core/quotes.fetch_quotes_live`: cascada Finnhub→Yahoo en paralelo, caché 15 s,
  circuito de 60 s tras HTTP 429 de Finnhub → `finnhub_quota:true`). Marketstack es
  solo respaldo EOD opcional y nunca pisa una cotización más nueva (merge por as_of).
  `/api/quote/<t>` y `/api/quotes` delegan en la misma función (devuelven además `c/pc/dp/t`
  crudos por compatibilidad). `LivePrices.seed()` se ELIMINÓ (1.090 req/min → 429): no recrear.
  Portafolio del usuario (UN solo lugar donde guardar, 2026-10-15): `MKT.pos` es la VISTA {nodeId:{sh,bp}} de la
  cartera ACTIVA de `kh_portfolios` (engine/pfstore.js, `window.KhipuPfStore`; escribir = `savePos()` → la activa);
  `eco_pos` es SOLO una copia escrita (nunca se lee como fuente; un eco_pos ajeno que llega del servidor se adopta en
  «Mi cartera», nunca se pisa). Todo se sincroniza por engine/sync.js (/api/user-state).
- `window.NODE_BY_ID` SÍ está expuesto (antes era undefined — rompía el Grafo
  Temporal en silencio; no quitar la línea `window.NODE_BY_ID = NODE_BY_ID`).
- `window.TEMPORAL_SEED_FACTS` + `window.ONTOLOGY` ({types, rels, objects})
  alimentan el Grafo Temporal cliente.
- Acciones de ontología: `actor` SIEMPRE obligatorio; el nombre del usuario se
  guarda en `localStorage.khipu_actor`.
- **API keys: SOLO en el server** (env vars de Railway). El modo standalone y
  el UI de keys en el navegador se ELIMINARON (2026-07); `SERVER_MODE` es
  constante `true` (se conserva la var porque engine/*.js la consulta) y
  `Keys.has(svc)` solo refleja `/api/health`. El PIN de trading del usuario
  vive en `localStorage.khipu_trade_pin` (header `X-Trade-Pin`).

## Funciones globales clave

- `switchTab(tab)`: tab ∈ {map, market, analysis, geo, simulation, space,
  terminal, canvas, tkg, guia} — `'sim'` NO existe, es `'simulation'`.
- `jumpTo(nodeId)` · `activateStress(nodeId)` · `renderMarket()` ·
  `computeNodeRadius(nodeId)`.
- `window.initTKGTab()` / `window.initGuiaTab()`: init perezoso de pestañas.
- `window.__tkgOpenObj(id)`: ficha de objeto del Grafo Temporal.
- `window.__tkgSetDate(fecha)`: mueve la línea de tiempo (lo usa KHIPU).
- `window.openSistema(tab?)`: overlay unificado 🩺 con tabs internas
  (diag / registro / propuestas). openDiagnostics/openRegistro/openPropuestas
  existen pero ya NO gestionan su propio panel — no recrear paneles sueltos.
- `window.KHIPU.tryParse(texto)`: parser de comandos — se intenta ANTES de
  llamar a la IA en command_center.js (devuelve null si no es comando).
- `window.openFinCard(idOrTicker)`: EL Dossier (📊) — funciona para TODO nodo
  (cotizada: franja en vivo + estados; no cotizada: ficha + dueño + noticias).
  Abrir desde botones con `_surface('dossier', id)` (queda sobre la Cabina).
  `window.KhipuLive.profile(ticker)`: perfil en vivo (caché 60 s).
- `window._openSecondBrain(nodeId)` · `window.BixbyVoice.toggle()` ·
  `window.nexusCore.runPreset(presetId)`.
- `window.KhipuResolve.find(texto)` (engine/resolve.js): resolutor robusto de
  empresas (aliases de transcripción de voz, fuzzy, sugerencias top-3) —
  TODO camino de entrada de nombres (voice/command_center/cockpit/khipu_lang)
  pasa por él. `KhipuResolve.notFound(q)` da el mensaje bilingüe.
- `window._surface(kind, arg)`: lo que Khipu muestra queda SIEMPRE al frente
  (dentro de la Cabina si está abierta; si no, switchTab + cierra overlays).
  No mostrar resultados sin pasar por _surface.
- `window.KhipuToast` (engine/toast.js): EL sistema de pop-ups/confirmaciones —
  `show({kind,title,body,mode})`, `confirm(opts)`, `confirmOrder(order)` y
  `order.sending/result/watch/filled`. Toda compra/venta (real o simulada) debe
  confirmar y notificar por aquí; no volver a `window.confirm` para dinero.
- `window.CRYPTO_INTEL` + `window.CRYPTO_CATS` (nodes/crypto_intel*.js):
  expediente cripto Top 50 bilingüe, capa estática jul-2026 (refrescar cada
  3-6 meses). UI en engine/crypto.js — tab 'crypto', vistas Mapa/Lista/Detalle.
- Actualizaciones de versión SIEMPRE silenciosas: _showUpdatePill ya NO
  muestra aviso (recarga al abrir o al ocultar pestaña — pedido explícito).
  No reintroducir pills/avisos de versión.
- Trading (papel por defecto): TODAS las rutas /api/trade/* exigen
  X-Trade-Pin (env TRADE_PIN; sin él → 403 y la UI muestra ese error tal
  cual). Cliente: usar SIEMPRE `window._tradeFetch(url, opts, interactive)`
  — nunca reimplementar el PIN. Cripto = símbolos 'BTC/USD' + notional USD;
  el server fuerza tif='gtc'. Badge obligatorio 🧪 SIMULADO / 🔴 DINERO REAL
  según `account.paper`. NINGUNA orden sin confirmación explícita (clic o
  sí verbal). Khipu (voz): place_order (flujo confirmed=false→resumen→sí→
  confirmed=true; `mode` paper|live sale de la cuenta REAL, nunca se asume papel) y get_account_status; broker en Cabina:
  `window._openBrokerStage()` / `_surface('trade')` sin arg.

## Lenguaje KHIPU (engine/khipu_lang.js)

`<TICKER|id> DES/GP/SUP/CLI/RISK/NEWS/SIM/FA/THESIS/XRAY [texto]` ·
`PORT VAR` (reporte de riesgo: engine/riskreport.js → POST /api/portfolio/risk_report, core/risk_report.py) / `PORT VEGA` (griegas de opciones: POST /api/portfolio/vega_report, core/options.py, Black-Scholes + IV en vivo) / `PORT PL` · `GRAPH ASOF <fecha>` / `GRAPH DIFF <Nd>` · `FEED [n]` (lo último del grafo) ·
`ALERT <ticker> PX|NRS > <valor>` / `ALERT REGION <región> NEWS` / `ALERT LIST` ·
`COMPARE <A> <B>` (comparador) · `SHOCK <ticker> [sev]` (sim en vivo) ·
`INSIGHTS` / `MATRIX` (pestaña Análisis) ·
`FACTOR LIST` / `FACTOR <id|texto> FIRE` (what-if de crisis de un factor
sistémico; ambigüedad → mayor severity_crisis + alternativas). Acciones
nuevas en command_center: xray, compare, insights, livesim.

## ScenarioBuilder / categorías

- `ScenarioBuilder.PRESETS` (objeto, no array): taiwan_conflict,
  china_chip_ban_total, hbm_shortage_2027, openai_ipo_impact, starshield_reveal.
- 40 categorías: CATS + CATS_NEW merged con Object.assign. CSS vars `--c-{cat}`.

## Reglas de despliegue — NO SALTARSE

1. **Bump del SW cache en CADA cambio de JS/HTML**: `sw.js` línea 6
   (`khipu-finance-vN` → vN+1). Sin esto los usuarios ven código viejo
   ("no veo los cambios" → pedir incógnito / Ctrl+Shift+R). Archivo JS nuevo →
   añadirlo también al array SHELL de sw.js.
2. Paneles de pestaña DENTRO de `<div class="app">` (cierra en
   `<!-- /.app -->`) — fuera quedan invisibles (bug real que ya pasó).
3. Flujo git: desarrollar en `claude/friendly-curie-moauj9` → commit →
   `git checkout main && git merge --ff-only` → push AMBAS ramas (con
   retry/backoff) → volver a la rama.
4. Verificar antes de commit: `node --check` en cada .js tocado;
   `py_compile` de los .py tocados; `node --check` de cada engine/app_*.js y los 4
   bloques inline que quedan en app.html con `new vm.Script()` (tests/test_app_split.py lo hace); `pytest tests/ -q` (~1.800 tests; los de ontología se
   auto-saltan sin DATABASE_URL). En la PC de Fabrizio (Windows) hay entorno
   completo instalado (2026-07): Python 3.11
   (`C:\Users\Dell\AppData\Local\Programs\Python\Python311\python.exe`) y
   PostgreSQL 16 local — correr TODO con:
   `DATABASE_URL=postgresql://postgres:devpass@localhost:5432/khipus_test pytest tests/ -q`

## Variables de entorno

```
SECRET_KEY, FINNHUB_KEY, ANTHROPIC_KEY, GEMINI_KEY, NVIDIA_KEY, AI_ORDER (solo nivel rápido; mejor borrarla), AI_ORDER_FAST, AI_ORDER_DEEP,
AI_MODEL_FAST, AI_MODEL_DEEP (AI_MODEL ya no existe),
ELEVENLABS_KEY, ELEVENLABS_AGENT_ID, ELEVENLABS_ALLOW_OVERRIDE,
AV_KEY, FMP_KEY, MARKETSTACK_KEY, ALPACA_KEY/SECRET/BASE,
TRADE_PIN            ← SIN esto el trading queda deshabilitado (X-Trade-Pin)
KHIPU_ADMIN_SECRET   ← emite claves /v1 de tiers de pago (X-Admin-Secret)
DATABASE_URL                              ← Ontología (Postgres en Railway)
RESEARCH_DAILY_BUDGET_USD, RESEARCH_AUTO_EVENTS, RESEARCH_MODEL_DEFAULT  ← Phase 2
RESEARCH_ANOMALY_PCT (8), RESEARCH_ANOMALY_MAX (3)  ← movimientos anómalos → investigación auto
RESEARCH_EARNINGS_MAX (5)  ← resultados trimestrales (Finnhub, requiere FINNHUB_KEY) → investigación auto
RESEARCH_OUTCOME_BAND (0.02), RESEARCH_CALIBRATION_K (10), COMMITTEE_MAX_CONCURRENT  ← Phase 3 (COMMITTEE_MEMO_TTL_HOURS ya no: vive en policy.committee)
BROKERAGE_ENC_KEY (Fernet; OBLIGATORIA para guardar llaves de clientes), BROKERAGE_TRADING_ENABLED (on),
BROKERAGE_LIVE_ENABLED (off), BROKERAGE_AUTO_APPROVE_PAPER (off), BROKERAGE_APPROVAL_TTL_MIN,
ALPACA_OAUTH_CLIENT_ID / ALPACA_OAUTH_CLIENT_SECRET / ALPACA_OAUTH_REDIRECT_URI  ← corretaje multi-cliente
MCP_ENABLED, MCP_TRADING_ENABLED, MCP_OAUTH_ENABLED, MCP_PUBLIC_URL, MCP_ALLOWED_ORIGINS/HOSTS  ← MCP
WORLD_GDELT_QUERY_CONFLICT / _UNREST / _TRADE, WORLD_GDELT_GEO_URL  ← World Monitor (ajustar sin tocar código)
FINNHUB_WS_KEY (clave Finnhub separada para el navegador), GUNICORN_THREADS (12), GUNICORN_MAX_REQUESTS (0 — dejar en 0),
AI_MAX_CONCURRENCY (4), AI_INTERACTIVE_RESERVE (1), AI_CLAUDE_TIMEOUT_S, DB_POOL_SIZE/DB_MAX_OVERFLOW (10/10),
DB_STATEMENT_TIMEOUT_MS, MATRIX_HEAVY_CONCURRENCY (1), REMIGRATE_ON_BOOT=<nombre de la base>  ← estructura
GEMINI_MODEL (gemini-3.8-flash), GEMINI_FALLBACK_MODEL (gemini-3.5-flash,gemini-3.1-pro)  ← Gemini
TYPESAFE_API_KEY (Jev), TYPESAFE_MODEL (jev-latest), DECIDE_SHADOW (on), DECIDE_CONTROL (vacío; 'chat_gate,…' o 'all'), DECIDE_TIMEOUT_S (6)  ← decisiones Jev
WORLD_SOURCE_DOWN_AFTER (3), WORLD_SOURCE_DOWN_TTL (3600)  ← W1: fuente con 404/403 seguidos en pausa 1 h
LOG_JSON (off)  ← O2: logs JSON con job_id/agente/proveedor/costo/latencia
KHIPU_MCP_TOKEN (secreto de GitHub Actions, NO de Railway)  ← O1: humo del MCP tras cada push (scope read)
AI_CIRCUIT_CREDIT_S (3600) / AI_CIRCUIT_AUTH_S (1800) / AI_CIRCUIT_MODEL_S (1800)  ← R1: pausa del proveedor tras error definitivo
AI_TRANSIENT_RETRIES (3), AI_TRANSIENT_BASE_S (1.5), AI_TRANSIENT_CAP_S (8)  ← R2: reintentos 429/5xx con backoff+jitter
RESEARCH_BUSY_RETRIES (4)  ← R2: esperas ante "IA ocupada" (3/6/12/24 s) antes de fallar el agente
RESEARCH_PARALLEL (2; nunca más que los cupos de fondo), RESEARCH_JOB_CONCURRENCY (2), RESEARCH_STALE_MIN (30), RESEARCH_RESUME_MAX (3)  ← R3/R5: cola de investigación
KHIPU_SCHEDULER (on; off en tests)  ← R5: reloj del servidor (core/scheduler.py) para lo diario
HOTVIEWS (on), HOT_WAIT_S (2), HOTVIEWS_COALESCE_S (1), HOTVIEWS_LISTEN (on)  ← vistas rápidas (core/hotviews)
PRICES_EOD (on), PRICES_REQ_INTERVAL_S (0.6)  ← historia de precios (core/prices_store: carga diaria tras las 22:00 UTC; el relleno de 5 años SOLO con PIN)
GOV_RELEASE (vacío = el vigente de la base), <ARTEFACTO>=<semver> p. ej. KERNEL_PARAMS  ← SOLO eligen un release aprobado (D2)
KHIPU_GATES (on; 'off' = emergencia: apaga las puertas SHACL en sombra)
GENUI (off; shadow = arma, mide y guarda en el libro SIN enviar; on = envía `ui` solo a quien manda context.genui=1)  ← chat con interfaz generativa (core/genui, docs/CHAT_UI_GENERATIVA.md)
── G5-14 (lote I4, 2026-10-13): TODA variable que el código lee está aquí (la bóveda: 0 sin documentar) ──
CLAUDE_KEY / ALPHA_VANTAGE_KEY / GOOGLE_API_KEY / NVIDIA_API_KEY / TYPESAFE_KEY  ← nombres ALTERNATIVOS de ANTHROPIC_KEY / AV_KEY / GEMINI_KEY / NVIDIA_KEY / TYPESAFE_API_KEY
ANTHROPIC_ADMIN_KEY (gasto real de Claude en 💰), AI_PRICES_JSON (precios extra por modelo), AI_DAILY_LIMIT_USD (10), AI_MONTHLY_LIMIT_USD (150), AI_PER_USER_DAILY_USD (0 = sin tope)  ← 💰 Gasto IA (los límites con PIN mandan)
AI_BUSY_WAIT_S (20), AI_CLAUDE_TIMEOUT_DEEP_S (110), GEMINI_HOT_S (180), GEMINI_THINKING (off)  ← IA: espera de cupo, tope del nivel profundo, pausa del modelo saturado, "pensar" en el nivel rápido
DECIDE_ENABLED (on), TYPESAFE_API_URL  ← Jev: apagarlo sin borrar la clave / otra URL
ELEVENLABS_LLM (vacío = el recomendado), BIXBY_AUTOSYNC (1; 0 = no sincronizar el agente de voz al arrancar)  ← voz
CSP_ENABLED (true), CSP_REPORT_ONLY (false)  ← seguridad del navegador (emergencia)
REDIS_URL (opcional: caché compartida), DB_POOL_TIMEOUT_S (10), DB_CONNECT_TIMEOUT_S (5), MATRIX_ENGINE (sparse|dense), MATRIX_BUSY_WAIT_S (3), INSIGHTS_INFLIGHT_WAIT_S (45), LIVE_DEADLINE_S (8)  ← estructura
COMMITTEE_MAX_SEATS, RESEARCH_DEDUPE_MINUTES (30), RESEARCH_HEARTBEAT_STALE_MIN (3), RESEARCH_MAX_AGENTS_PER_JOB (4), INVESTIGADOR_AUTO (off), INVESTIGADOR_AUTO_CUTOFF_HORAS (6), TAVILY_KEY, SEC_USER_AGENT  ← investigación/comité
MCP_RATE_PER_MIN (60), MCP_RESEARCH_PER_HOUR (10), MCP_TRADE_PER_HOUR (30), MCP_MAX_INFLIGHT (3), MCP_MAX_INFLIGHT_TOTAL (5), MCP_PIN_MAX_FAILS (10), MCP_PIN_LOCK_MIN (30), MCP_OAUTH_TTL_HOURS, MCP_STATIC_TOKEN, MCP_TRUSTED_PROXY_HOPS (1)  ← MCP
COINGECKO_KEY, CLOUDFLARE_RADAR_TOKEN, SPACE_LL2_BASE, WORLD_GDELT_EVENTS (on), WORLD_GDELT_BACKFILL (on), WORLD_GDELT_EVENTS_BASE, WORLD_GPR_DAILY_URL, WORLD_GPR_MONTHLY_URL, WORLD_PORTWATCH_URL, WORLD_FEDREG_URL, WORLD_GDACS_URL, WORLD_ADVISORIES_URL  ← fuentes en vivo (URLs: solo si el proveedor se muda)
RAILWAY_GIT_COMMIT_SHA, RAILWAY_PUBLIC_DOMAIN, RAILWAY_ENVIRONMENT, RAILWAY_ENVIRONMENT_NAME, RAILWAY_PROJECT_ID  ← las pone Railway solo (sello del código; URL del MCP; "estamos en producción")
GUNICORN_MAX_REQUESTS_JITTER (0; solo Dockerfile) · OPENAI_KEY: solo un comentario de docker-compose (no se usa) · ANTHROPIC_API_KEY / TAVILY_API_KEY: solo en la lista de secretos que se tapan en los logs
KHIPU_URL, SMOKE_RETRIES, GITHUB_OUTPUT, GITHUB_STEP_SUMMARY  ← SOLO scripts de GitHub Actions (humo del MCP, ancla del libro), no Railway
KH_GUARD_TRACE  ← solo diagnóstico/pruebas de la guardia del libro
KH_SCALE (vacío; 1 = corre las pruebas lentas de escala: test_scale_budget, test_scale_kernel 10k/20k, test_scale_tensor_5k)  ← solo pruebas, no Railway
(BROKERAGE_APPROVAL_TTL_MIN, RESEARCH_CALIBRATION_K, RESEARCH_OUTCOME_BAND: ya NO cambian números — viven en policy.*; el 🩺 avisa si siguen puestas)
```

## Multi-IA — HÍBRIDA (2026-07-12)

`core.ai._ai_complete(system, prompt, max_tokens, tier='fast')` intenta
los proveedores en cascada según el orden DEL NIVEL (ver abajo; el alias `_claude_complete` y la
variable `AI_MODEL` se borraron en la limpieza 2026-10-11). Dos niveles (el tier cambia el orden de
proveedores y el modelo Claude): `AI_MODEL_FAST` (env, default claude-haiku-4-5) para
comandos/noticias/alertas/radar; `AI_MODEL_DEEP` (env, default
claude-sonnet-5-5) para síntesis de deep research, tesis/veredicto IA, Canvas,
War Room y brief matinal. `/api/ai/analyze` acepta `tier:'deep'` en el body
(el tier forma parte de la cache key). Cliente:
`DataLayer.aiComplete(system, prompt, maxTokens, tier)`.
`_extract_json()` tolera JSON envuelto en prosa/fences (Gemini/NVIDIA).
**Orden por nivel (2026-10-10)**: `AI_ORDER_DEEP` (defecto claude,gemini,nvidia; ignora AI_ORDER) y `AI_ORDER_FAST` >
`AI_ORDER` > gemini,claude,nvidia (`provider_order`, `ai_route_state`). Claude por modelo con `claude_attempts`: Sonnet 5.5
NUNCA thinking disabled ni temperature; Opus 5.5/Fable nunca disabled; un 400 de parámetros reintenta el MISMO modelo.
El 🩺 muestra la ruta REAL por nivel (`/api/diagnostics` → `routing`). Voz: `core/voice_agent.py` es el ÚNICO
cliente REST de ElevenLabs (desde 2026-10-11 también `list_voices`/`adopt_shared_voice`; server.py ya no llama a
api.elevenlabs.io — un test lo vigila). Las instrucciones de la voz (`BIXBY_SYSTEM_PROMPT`) describen Khipus OS
y toman los agentes del registro único.
**Gemini 3+ (2026-10-06, default `gemini-3.8-flash`)**: NO acepta `thinkingBudget` (ni 0 ni "minimal" → 400);
`_complete_gemini_inner` manda `thinkingLevel` low (chat/rápido) o medium (profundo, también investigación JSON) con margen de tokens.
Precio en `core/ai_usage.PRICES` (0,75/3,75 hasta 31-dic-2026; luego 1,5/7,5 → actualizar).
Si Google satura (503/429/5xx) o retira (404) el principal, el mismo pedido va a `GEMINI_FALLBACK_MODEL`
(lista con comas; default gemini-3.5-flash,gemini-3.1-pro; 'off' lo apaga; un respaldo con 404 se salta 6 h y nunca pausa todo Gemini) antes de saltar a NVIDIA;
entre modelos no se reintenta (salta al instante) y los saturados van al final 3 min (`gemini_state()`, salud).
server.py y ontology/agents.py importan de core/ — no redefinir en el server.
**GUARDIÁN DE CIFRAS (2026-09-28, pedido explícito "todo en vivo, los datos
falsos perjudican al inversionista")**: `_ai_complete` añade NUMBERS_RULE al
system y verifica (core/numbers.py) que toda cifra de la respuesta esté en los DATOS del prompt (no en el system ni
en sus ejemplos); si no → 1 reintento con feedback y, si persiste,
la marca "(⚠ cifra no verificada)" en el tramo exacto. BLOQUE 0 (2026-10-12): compara por TIPO (dinero, %, múltiplos,
indicadores) con tolerancia por la precisión mostrada (precio ≤0,5 %), entiende "233,95 USD", "dólares", €/£/¥/NT$/S/
y separadores es/en, respeta el signo, exime fechas/años/condicionales y no tiene regex cuadráticas (50k dígitos
0,05 s). La simulación por agentes solo revisa dinero. Las cifras DERIVADAS (sumas, distancia al máximo) se marcan:
la IA debe copiar, no calcular. `_ai_complete_raw` = sin guardián (solo
lo usa el guardián). research/ usa check_numbers (rechazo estricto). Para que
la IA dé cifras correctas, `core/live_facts.py` anexa a TODO prompt un
bloque "DATOS EN VIVO" (capitalización+precio del perfil en vivo; privadas:
última valuación VERIFICADA con fecha) de las empresas mencionadas (máx 4,
6 s, nunca rompe la llamada).

## Errores comunes

- **NO correr `REMIGRATE_ON_BOOT` sobre la base de producción**: es la base
  ORIGINAL (1.294 objetos, reconectada 2026-09-22), con ~216 objetos que el
  repo no puede reconstruir. Es destructiva. Solo para bases nuevas y vacías.
- **ENDURECIMIENTO 2026-09-30 (auditoría estructural, no revertir)**:
  - PIN: `core/pin.py` es el ÚNICO verificador (trade, brokerage, MCP, comité,
    escrituras de ontología con `require_operator`). En el cliente el PIN dura
    12 h (`khipu_trade_pin` + `khipu_trade_pin_exp`): leer SIEMPRE con
    `window._tradePinStored()` / guardar con `_tradePinSave()`; llamadas con
    PIN SIEMPRE por `window._tradeFetch(url, opts, interactive)` (acepta
    `opts.timeout`).
  - Órdenes: `client_order_id` en todo envío (`_tradeOrderId`/`_tradeOrderSettle`/
    `_tradeOrderIsDup`, pendientes en `khipu_coid_pending` 24 h); el panel ya NO
    simula en silencio si falla (solo con trading_disabled/broker_not_configured).
  - Enlaces externos: `window.safeUrl(u)` (solo http/https, escapado) + guard de
    clic que bloquea javascript:/vbscript:/data:. `esc()` escapa `'`.
  - Service worker: NUNCA cachea /api, /v1, /mcp, /oauth, /.well-known (offline
    → JSON 503 {offline:true}); estático solo si res.ok && basic; navegación con
    10 s de límite → shell guardado con `window.__KHIPU_STALE_SHELL=1`; la
    franja roja de "servidor no disponible" vive en el PRIMER bloque inline.
    `const CACHE` debe quedar en los primeros 2048 caracteres de sw.js
    (server._sw_version los lee para el ?v=N).
  - `window.khJSON(r)` valida que la respuesta sea JSON; `window.LANG` ahora es
    un getter (antes los módulos engine/* leían undefined).
  - Server: errores JSON en /api; `@cache.cached` no guarda errores (fallbacks
    60 s); IA con timeout y semáforo (AI_MAX_CONCURRENCY 4, reserva interactiva
    1); DB con pool/statement timeout; matrix con topes y semáforo pesado.
  - `REMIGRATE_ON_BOOT` ahora debe ser EXACTAMENTE el nombre de la base (una
    vez; `<nombre>:2` para repetir) y NUNCA borra tablas broker_*/mcp_*/research_*.
  - requirements + `constraints.txt` (versiones exactas) — no quitar.
- **Mapa principal**: la física se asienta SIN dibujar (`settleGraph()`); solo
  el arrastre pinta en vivo (`_liveTick`). No reintroducir `sim.alpha().restart()`
  fuera del drag: son ~11.000 escrituras al DOM por fotograma.

- **Los proveedores de IA RETIRAN modelos.** En sept-2026 Gemini (404) y NVIDIA
  (410) cayeron a la vez por eso, justo cuando Claude se quedó sin saldo: cero
  red de seguridad. El arreglo NUNCA es tocar código — es `GEMINI_MODEL` /
  `NVIDIA_MODEL` en Railway. El 🩺 ya lo dice explícitamente (`_ai_error_hint`).

- **SQLAlchemy 2.1 usa psycopg 3 por defecto** (no instalado) → en sept-2026
  un redeploy la instaló y TODA la ontología dio "No module named 'psycopg'".
  requirements fija `<2.1` y `ontology/db._normalize_url` fuerza `+psycopg2`.
  No quitar ninguna de las dos.

- `switchTab('sim')` → INCORRECTO, es `'simulation'`.
- Olvidar el bump de sw.js → los usuarios ven código viejo.
- Panel de pestaña fuera de `.app` → pantalla negra.
- Usar `/v1/*` para features internas → colisiona con la API monetizada.
- `getCatColorHex()`/`getLinkColorHex()` viven en engine/app_main.js (antes inline en app.html) y son las
  ÚNICAS definiciones: la copia de graph3d.js se borró en Track A Fase 2
  porque pisaba a la de app.html en silencio. No reintroducirla.
- Atributos SVG no resuelven `var(--css)` — usar hex directo.
- rAF se congela en pestañas ocultas — voice.js usa `_defer()` con fallback a
  setTimeout cuando `document.hidden` (no revertir).
- MAX_CONTENT_LENGTH es 1 MB — payloads de contexto grandes (Canvas) lo rozan.

## Nombres y usuario

- App: **Khipus Finance Intelligence** (2026-10-10; antes "Khipus Finance AI", renombrada 2026-08-03 — "Bixby" es marca de
  Samsung y Fabrizio no puede usarla; antes fue "Bixby Finance" y
  originalmente "Khipus AI Finance Inteligence"). Asistente/voz: **Khipu**
  (nombre PROVISIONAL — Fabrizio buscará el definitivo; cuando llegue,
  repetir el sed protegido: blindar primero los identificadores
  Bixby(CC|Cockpit|Level|Orb|Thinking|Voice), que NO se renombraron, y las
  clases CSS/ids 'bixby-*' minúsculas tampoco; el matcher de transcripción en
  voice.js acepta 'khipu:' y 'bixby:'). SOLO se renombra lo VISIBLE;
  identificadores internos NO cambian (caché sw 'khipu-finance-vN',
  localStorage 'khipu_*'/'kh_*', globals Bixby*/KhipuResolve/KhipuLocalCharts/
  KhipuPortfolios/KhipuUniverse2D, window.KHIPU DSL, engine/khipu_lang.js,
  /v1/* monetizada) — cambiarlos rompería estados/caché.
- Usuario (Fabrizio): hispanohablante, no técnico. Explicar en español simple,
  sin jerga; pasos con clics exactos para Railway/etc.; siempre cerrar
  con "qué hacer ahora" concreto. La pestaña ❓ Guía de la app existe para él.
  **Mensajes CORTOS estilo TDAH (pedido 2026-10-13: "los mensajes largos me quitan atención")**: viñetas breves con
  emoji de sección, lo esencial primero, máximo ~10 líneas, sin párrafos largos.
- La interfaz debe tender a SIMPLIFICARSE: antes de añadir un botón/ícono
  nuevo, evaluar fusionarlo con uno existente (pidió esto explícitamente).
- **REGLA BILINGÜE (2026-07-12, pedido explícito)**: TODO texto de UI nuevo
  debe existir en español E inglés, conmutado por el botón de idioma
  (`LANG`/`t()`/`I18N` en engine/app_main.js; módulos engine/* usan su propio dict
  {es,en} leyendo `window.LANG` o `localStorage.eco_lang`). Nunca shippear
  strings solo en un idioma.
- **EXPLICABILIDAD (2026-07-12)**: la app la usan inversionistas NO expertos —
  toda métrica (NRS, VaR, w, chokepoint…) debe tener su "?" que la explique
  en lenguaje simple (engine/explain.js, `window.explainMetric(key)`).
