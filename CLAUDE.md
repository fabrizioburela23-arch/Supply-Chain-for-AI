# Khipus AI Finance Inteligence — CLAUDE.md

Terminal financiero (estilo Bloomberg + ontología estilo Palantir) para la
cadena de suministro de semiconductores, IA, espacio y nuclear. 407 empresas
canónicas, 1,028 relaciones (dirección ÚNICA: source PROVEE a target; 9 tipos
de relación; 9 macro-sectores en SECTORS9). Desplegado en Railway (push a
`main` auto-deploya, ~2 min).

**Al iniciar una sesión de trabajo: lee `docs/ESTADO.md`** — es la memoria
entre sesiones (qué se construyó, decisiones tomadas, qué falta).
`docs/AUDITORIA.md` = inventario de dónde vive cada dato.

## Arquitectura

- `app.html` (~12,300 líneas): TODA la UI en un archivo, 8 bloques `<script>`
  inline. Tabs: map, market, analysis, geo, simulation, space, terminal,
  canvas, tkg (◈ Grafo Temporal), guia (❓ Guía).
- `server.py` (~2,500 líneas): Flask sync + gunicorn **1 worker + 8 threads**
  (NO subir workers: el estado en memoria — caché, rate limits, agente de
  trading — divergiría entre workers). Proxy de todas las APIs externas.
- `core/` (paquete Python): helpers compartidos server/ontology/matrix —
  `config.py` (keys IA/Finnhub/timeout), `http.py` (_safe_get/_safe_ticker),
  `ai.py` (cascada Claude→Gemini→NVIDIA + _extract_json), `quotes.py`
  (_fetch_quote_raw). Rompe la dependencia circular ontology→server.
- `matrix/` (paquete Python, opcional): motor de matrices — `engine.py`
  (build_matrices por rel_type + as_of, active_factors=hiperaristas,
  fragility, propagate=EL kernel de shocks, compute_metrics/chokepoints),
  `api.py` (blueprint /api/matrix/*: status, /<rel_type>, POST /impact,
  /metrics). Convención A[i,j]=i PROVEE a j. Sin DATABASE_URL → 503.
- `ontology/` (paquete Python): ontología Palantir-style —
  `models.py` (events bitemporal + objects/links materializados +
  ProposedAction + Alert), `service.py` (apply_event, as_of_graph, diff_graph),
  `actions.py` (catálogo de 9 Acciones auditadas, Pydantic), `agents.py`
  (4 agentes + brief matinal + evaluador de alertas), `api.py` (blueprint).
- `engine/`: temporal-graph.js (~1,050 líneas, Grafo Temporal), khipu_lang.js
  (parser de comandos), guide.js (Guía), voice.js (Bixby voz/ElevenLabs),
  command_center.js (Bixby texto), graph3d.js, geoglobe.js, planetarium.js,
  secondbrain.js, canvas-data.js, hypergraph.js, geo_coords.js.
  REDISEÑO 2026-07 (piel NEXUS): xray.js (X-Ray de empresa), statematrix.js
  (motor de estados reactivo cliente, MISMA matemática que matrix/engine.py),
  livesim.js (simulación en vivo sobre el mapa), layers.js (capas del mapa),
  insights.js (tarjetas #an-insights), brief.js (brief matinal). Todos leen
  window.NODES/LINKS/computeNRS/SECTORS9 y degradan sin DATABASE_URL.
- `nodes/`: catálogo de empresas (nodes_*.js) + links (links_*.js) +
  ontology.js/ontology_facts.js (tipos y hechos tipados) +
  temporal_seed_facts*.js (105 hechos con fechas reales) + preipo_intel.js.
- `scripts/`: export_graph_v0.js (snapshot) · migrate_v0_to_ontology.py.
- `data/grafo_v0.json`: snapshot canónico (407 nodos / 1,028 links) — se
  regenera con `node scripts/export_graph_v0.js` (usa nodes/merge_graph.js,
  la MISMA implementación de merge que el navegador; nunca duplicar).
- `sim/`: mirofish_client.js, scenario_builder.js.
- ELIMINADOS en la limpieza 2026-07 (no recrear): `rag/` (nunca desplegado),
  `litellm/`, `nodes/nodes_core.js` (duplicado), el modo standalone completo
  y el stack de keys en el navegador.

## Dos bases de datos — roles distintos, NO fusionar

- **Postgres** (`DATABASE_URL`, plugin de Railway): FUENTE ÚNICA DE VERDAD de
  la ontología. Eventos inmutables con `valid_from/valid_to` (validez) +
  `recorded_at` (sistema). Time-travel: `GET /api/ontology/graph?as_of=`.
- **Neo4j Aura** (`NEO4J_URI/USER/PASSWORD`): espejo visual del Grafo
  Temporal. Si cae, la app sigue en modo nativo.
- Ambas OPCIONALES: sin sus env vars el server arranca igual (patrón
  try/except + `*_available()`). Nunca romper ese patrón.

## Namespaces de API — CRÍTICO

- `/api/*` — endpoints internos de la app.
- `/api/ontology/*` — ontología (objects, graph, actions, agents, alerts).
- `/v1/*` — **API pública MONETIZADA por tiers (JWT, `khipu_auth`). NO tocar,
  NO usar para features internas.**

## Convenciones de datos críticas

- `computeNRS(nodeId)` → NUMBER 0-100, NO objeto. Memoizado (`_nrsCache`);
  llamar `window._invalidateNRS()` si LINKS cambia. OJO: la fórmula cliente no
  acota el término de margen (pre-revenue infla el score); la réplica server
  (`ontology/agents.py:_compute_server_nrs`) SÍ acota [0,20] — divergencia
  conocida y documentada.
- `RAW_LINKS`: arrays `[s, t, w, rel, type]`; los `{s,t,type}` de
  links_expand.js se convierten en el merge; `NODE_ID_ALIAS` normaliza ids.
- `LINKS` (post-merge): objetos `{source, target, w, rel, type}` — usar
  `lid(l.source)` para el id.
- `MKT.quotes[ticker] = {close, prev, live}` — NO usar `q.c` ni `q.pc`.
  Portafolio del usuario: `MKT.pos` en localStorage (NO en el server aún).
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
- `window._openSecondBrain(nodeId)` · `window.BixbyVoice.toggle()` ·
  `window.nexusCore.runPreset(presetId)`.
- `window.KhipuResolve.find(texto)` (engine/resolve.js): resolutor robusto de
  empresas (aliases de transcripción de voz, fuzzy, sugerencias top-3) —
  TODO camino de entrada de nombres (voice/command_center/cockpit/khipu_lang)
  pasa por él. `KhipuResolve.notFound(q)` da el mensaje bilingüe.
- `window._surface(kind, arg)`: lo que Bixby muestra queda SIEMPRE al frente
  (dentro de la Cabina si está abierta; si no, switchTab + cierra overlays).
  No mostrar resultados sin pasar por _surface.
- `window.CRYPTO_INTEL` + `window.CRYPTO_CATS` (nodes/crypto_intel*.js):
  expediente cripto Top 50 bilingüe, capa estática jul-2026 (refrescar cada
  3-6 meses). UI en engine/crypto.js — tab 'crypto', vistas Mapa/Lista/Detalle.
- Actualizaciones de versión SIEMPRE silenciosas: _showUpdatePill ya NO
  muestra aviso (recarga al abrir o al ocultar pestaña — pedido explícito).
  No reintroducir pills/avisos de versión.

## Lenguaje KHIPU (engine/khipu_lang.js)

`<TICKER|id> DES/GP/SUP/CLI/RISK/NEWS/SIM/FA/THESIS/XRAY [texto]` ·
`PORT VAR/PL` · `GRAPH ASOF <fecha>` / `GRAPH DIFF <Nd>` ·
`ALERT <ticker> PX|NRS > <valor>` / `ALERT REGION <región> NEWS` / `ALERT LIST` ·
`COMPARE <A> <B>` (comparador) · `SHOCK <ticker> [sev]` (sim en vivo) ·
`INSIGHTS` / `MATRIX` (pestaña Análisis). Acciones nuevas en command_center:
xray, compare, insights, livesim.

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
   `py_compile` de los .py tocados; los 8 bloques inline de app.html con
   `new vm.Script()`; `pytest tests/ -q` (51 tests; los de ontología se
   auto-saltan sin DATABASE_URL). En la PC de Fabrizio (Windows) hay entorno
   completo instalado (2026-07): Python 3.11
   (`C:\Users\Dell\AppData\Local\Programs\Python\Python311\python.exe`) y
   PostgreSQL 16 local — correr TODO con:
   `DATABASE_URL=postgresql://postgres:devpass@localhost:5432/khipus_test pytest tests/ -q`

## Variables de entorno

```
SECRET_KEY, FINNHUB_KEY, ANTHROPIC_KEY, GEMINI_KEY, NVIDIA_KEY, AI_ORDER,
ELEVENLABS_KEY, ELEVENLABS_AGENT_ID, ELEVENLABS_ALLOW_OVERRIDE,
AV_KEY, FMP_KEY, MARKETSTACK_KEY, ALPACA_KEY/SECRET/BASE,
TRADE_PIN            ← SIN esto el trading queda deshabilitado (X-Trade-Pin)
KHIPU_ADMIN_SECRET   ← emite claves /v1 de tiers de pago (X-Admin-Secret)
MIROFISH_URL, MIROFISH_TOKEN,
NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,   ← Grafo Temporal persistente
DATABASE_URL                              ← Ontología (Postgres en Railway)
```

## Multi-IA — HÍBRIDA (2026-07-12)

`core.ai._ai_complete(system, prompt, max_tokens, tier='fast')` intenta
AI_ORDER (claude,gemini,nvidia) en cascada; `_claude_complete` es alias
compat. Dos niveles (el tier SOLO cambia el modelo Claude; Gemini/NVIDIA lo
ignoran): `AI_MODEL_FAST` (env, default AI_MODEL → claude-haiku-4-5) para
comandos/noticias/alertas/radar; `AI_MODEL_DEEP` (env, default
claude-sonnet-5) para síntesis de deep research, tesis/veredicto IA, Canvas,
War Room y brief matinal. `/api/ai/analyze` acepta `tier:'deep'` en el body
(el tier forma parte de la cache key). Cliente:
`DataLayer.aiComplete(system, prompt, maxTokens, tier)`.
`_extract_json()` tolera JSON envuelto en prosa/fences (Gemini/NVIDIA).
server.py y ontology/agents.py importan de core/ — no redefinir en el server.

## Errores comunes

- `switchTab('sim')` → INCORRECTO, es `'simulation'`.
- Olvidar el bump de sw.js → los usuarios ven código viejo.
- Panel de pestaña fuera de `.app` → pantalla negra.
- Usar `/v1/*` para features internas → colisiona con la API monetizada.
- `getCatColorHex()` vive en engine/graph3d.js — no existe antes de cargar.
- Atributos SVG no resuelven `var(--css)` — usar hex directo.
- rAF se congela en pestañas ocultas — voice.js usa `_defer()` con fallback a
  setTimeout cuando `document.hidden` (no revertir).
- MAX_CONTENT_LENGTH es 1 MB — payloads de contexto grandes (Canvas) lo rozan.

## Nombres y usuario

- App: **Khipus AI Finance Inteligence** (grafía del usuario; antes "Khipu
  Finance"). Voz: **Bixby** (ElevenLabs, no el de Samsung).
- Usuario (Fabrizio): hispanohablante, no técnico. Explicar en español simple,
  sin jerga; pasos con clics exactos para Railway/Neo4j/etc.; siempre cerrar
  con "qué hacer ahora" concreto. La pestaña ❓ Guía de la app existe para él.
- La interfaz debe tender a SIMPLIFICARSE: antes de añadir un botón/ícono
  nuevo, evaluar fusionarlo con uno existente (pidió esto explícitamente).
- **REGLA BILINGÜE (2026-07-12, pedido explícito)**: TODO texto de UI nuevo
  debe existir en español E inglés, conmutado por el botón de idioma
  (`LANG`/`t()`/`I18N` en app.html; módulos engine/* usan su propio dict
  {es,en} leyendo `window.LANG` o `localStorage.eco_lang`). Nunca shippear
  strings solo en un idioma.
- **EXPLICABILIDAD (2026-07-12)**: la app la usan inversionistas NO expertos —
  toda métrica (NRS, VaR, w, chokepoint…) debe tener su "?" que la explique
  en lenguaje simple (engine/explain.js, `window.explainMetric(key)`).
