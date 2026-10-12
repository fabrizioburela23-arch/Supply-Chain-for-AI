---
tipo: "reporte"
tags: ["tipo/reporte"]
---

# 01 Reporte del grafo

Lo calcula `scripts/build_vault.py` leyendo el código (sin IA). Sirve para encontrar **cosas sueltas**: código sin pruebas, módulos o rutas que nadie usa, variables sin documentar.

> [!info] Cómo se decide "nadie lo usa" (heurística, revisar antes de borrar nada)
> - **Python**: cuenta como uso cualquier `import`/`from … import` (también dentro de funciones) y el nombre del módulo con puntos escrito como texto (`importlib.import_module("core.world")`, la lista de blueprints de server.py). Una palabra suelta (`"server"`, `"research"`) solo cuenta dentro de `import_module(…)`, `__import__(…)` o `sys.modules.get(…)`: si no, es una categoría o una clave, no una importación. Son puertas de entrada (no se reportan): `server.py`, los scripts de `scripts/`, todo módulo con `if __name__ == "__main__"`, los `__init__.py` y `tests/conftest.py`.
> - **JavaScript**: una global es `window.X = …` (o `Object.defineProperty(window, "X")`). Para las conexiones del grafo cuenta como uso que otro archivo escriba `X` en su código (no como clave de un objeto `{ X: … }`) o `window.X`, o la use dentro de un texto/HTML como `X(…)`, `X.algo` o `window.X` (los `onclick="…"`); la palabra suelta en un texto no cuenta. Para la lista de "nadie la usa" se es más generoso (cualquier mención, también del Python del servidor), así que lo que aparece ahí casi seguro sobra. No detecta accesos dinámicos (`window[nombre]`).
> - **Rutas**: cuenta como llamada cualquier texto que empiece por `/api`, `/v1`, `/mcp`… en JS, Python del servidor, scripts o pruebas; un texto que termina en `/` se trata como prefijo de las rutas que siguen. Una base como `var API = "/api/brokerage"` se une a las rutas relativas que el mismo archivo arma (`"/clients/" + id + "/audit"` → `/api/brokerage/clients/<id>/audit`); solo si el archivo no arma ninguna vale como prefijo de todas. Las rutas externas (`/v1/*` monetizada, `/mcp`, OAuth y su `…/oauth/callback`, `/api/health` de Railway, archivos estáticos) no se reportan.
> - **Pruebas**: un módulo está cubierto si una prueba lo importa o escribe su ruta (`engine/x.js`) o su nombre de archivo entre comillas.

## Conteos

| Qué | Cuántos |
|---|---|
| Archivos de código (Python, JS, HTML) | 177 |
| Líneas de código | 108.856 |
| Archivos de datos del catálogo | 28 |
| Archivos de prueba | 124 |
| Documentos | 24 |
| Rutas HTTP | 228 |
| Grupos de API | 57 |
| Herramientas MCP | 23 |
| Variables de entorno | 159 |
| Sesiones de trabajo | 90 |
| Aristas `calls_endpoint` | 552 |
| Aristas `defines_endpoint` | 251 |
| Aristas `imports` | 1.012 |
| Aristas `loads_script` | 78 |
| Aristas `mentions_in_session` | 490 |
| Aristas `reads_env` | 219 |
| Aristas `references_file` | 50 |
| Aristas `tested_by` | 749 |
| Aristas `uses_global` | 341 |

## Nodos "dios" (más conectados)

Conexiones de código entre archivos (importa, usa globales, carga, nombra, llama a su ruta). Mucho acoplamiento = cambiar ahí afecta a muchos.

| Archivo | Total | Entran | Salen | Capa |
|---|---|---|---|---|
| [[app.html]] | 137 | 52 | 85 | [[Capa Interfaz (Khipus OS)]] |
| [[server.py]] | 75 | 24 | 51 | [[Capa Infraestructura]] |
| [[engine.cockpit.js]] | 41 | 11 | 30 | [[Capa Interfaz (Khipus OS)]] |
| [[nodes.nodes_seed.js]] | 35 | 35 | 0 | [[Capa Datos del catálogo]] |
| [[ontology.db.py]] | 33 | 28 | 5 | [[Capa Ontología y grafo temporal]] |
| [[core.http.py]] | 32 | 30 | 2 | [[Capa Infraestructura]] |
| [[mcp_server.tools.py]] | 29 | 5 | 24 | [[Capa MCP y API]] |
| [[core.khipu_chat.py]] | 27 | 6 | 21 | [[Capa Chat y agentes]] |
| [[engine.voice.js]] | 27 | 5 | 22 | [[Capa Voz]] |
| [[engine.resolve.js]] | 26 | 17 | 9 | [[Capa Chat y agentes]] |
| [[engine.xray.js]] | 26 | 11 | 15 | [[Capa Interfaz (Khipus OS)]] |
| [[research.committee_api.py]] | 24 | 7 | 17 | [[Capa Comité]] |
| [[research.runner.py]] | 24 | 8 | 16 | [[Capa Investigación]] |
| [[core.world.py]] | 23 | 15 | 8 | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] |
| [[engine.khipu_chat.js]] | 23 | 5 | 18 | [[Capa Chat y agentes]] |
| [[ontology.api.py]] | 23 | 7 | 16 | [[Capa Ontología y grafo temporal]] |
| [[research.committee.py]] | 22 | 6 | 16 | [[Capa Comité]] |
| [[scripts.export_graph_v0.js]] | 22 | 0 | 22 | [[Capa Datos del catálogo]] |
| [[core.ai.py]] | 21 | 16 | 5 | [[Capa Infraestructura]] |
| [[engine.committee.js]] | 21 | 11 | 10 | [[Capa Comité]] |

## Módulos sin pruebas (23)

Código (no datos) que ninguna prueba importa ni nombra. Ordenado por tamaño.

| Módulo | Líneas | Capa |
|---|---|---|
| [[engine.worldmonitor.js]] | 1.326 | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] |
| [[engine.spacemonitor.js]] | 1.324 | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] |
| [[engine.universe2d.js]] | 1.048 | [[Capa Interfaz (Khipus OS)]] |
| [[engine.command_center.js]] | 433 | [[Capa Chat y agentes]] |
| [[scripts.ingest_enrichment_md.py]] | 404 | [[Capa Datos del catálogo]] |
| [[engine.orb.js]] | 396 | [[Capa Voz]] |
| [[engine.maptime.js]] | 389 | [[Capa Ontología y grafo temporal]] |
| [[engine.termdata.js]] | 359 | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] |
| [[scripts.ingest_multicapa.py]] | 343 | [[Capa Datos del catálogo]] |
| [[core.country_geo.py]] | 222 | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] |
| [[engine.matrixview.js]] | 207 | [[Capa Cuantitativo (matrices, tensores, riesgo)]] |
| [[core.screener.py]] | 185 | [[Capa Cuantitativo (matrices, tensores, riesgo)]] |
| [[security_audit.py]] | 182 | [[Capa Infraestructura]] |
| [[engine.compare.js]] | 168 | [[Capa Cuantitativo (matrices, tensores, riesgo)]] |
| [[research.contradictions.py]] | 143 | [[Capa Investigación]] |
| [[engine.layers.js]] | 133 | [[Capa Interfaz (Khipus OS)]] |
| [[core.providers.coingecko.py]] | 123 | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] |
| [[engine.nav4.js]] | 118 | [[Capa Interfaz (Khipus OS)]] |
| [[scripts.reconcile_v0_to_ontology.py]] | 101 | [[Capa Ontología y grafo temporal]] |
| [[engine.canvas-data.js]] | 72 | [[Capa Chat y agentes]] |
| [[scripts.build_private_valuations.py]] | 71 | [[Capa Datos del catálogo]] |
| [[scripts.build_listing_status.py]] | 63 | [[Capa Datos del catálogo]] |
| [[core.decide_api.py]] | 25 | [[Capa Chat y agentes]] |

## Módulos Python que nadie importa (0)

_Ninguno._

## Globales window.* que ningún otro archivo usa (40)

Se exportan a `window` pero nadie más las lee. Si "se usa dentro de su archivo" dice sí, la función sí trabaja (solo sobra la exportación); si dice no, es candidata a código muerto.

| Global | Definida en | ¿Se usa dentro de su archivo? | ¿La nombra alguna prueba? |
|---|---|---|---|
| `window.APP_NAME` | [[app.html]] | **no** | no |
| `window.ASSISTANT_NAME` | [[app.html]] | **no** | no |
| `window.DESC_FILL` | [[nodes.meta_fill.js]] | sí | no |
| `window.KhipuGeoGlobe` | [[engine.globe.js]] | **no** | no |
| `window.KhipuLiveCaps` | [[app.html]] | **no** | no |
| `window.KhipuLiveFund` | [[app.html]] | **no** | no |
| `window.KhipuOSWin_memoLine` | [[engine.oswindows.js]] | **no** | no |
| `window.KhipuVoiceAudio` | [[engine.voice.js]] | **no** | sí (solo pruebas) |
| `window.META_CHINA` | [[nodes.nodes_china.js]] | sí | no |
| `window.META_FILL` | [[nodes.meta_fill.js]] | sí | no |
| `window.OntologyAlerts` | [[app.html]] | sí | no |
| `window.Planetarium` | [[engine.globe.js]] | **no** | no |
| `window._briefAutoAllowed` | [[engine.brief.js]] | **no** | sí (solo pruebas) |
| `window._buildNrsDegree` | [[app.html]] | sí | sí (solo pruebas) |
| `window._cvRows` | [[app.html]] | **no** | no |
| `window._initGeoGlobe` | [[app.html]] | **no** | no |
| `window._layersApply` | [[engine.layers.js]] | **no** | no |
| `window._lblOn` | [[app.html]] | sí | sí (solo pruebas) |
| `window._mapState` | [[app.html]] | **no** | sí (solo pruebas) |
| `window._pfPendingAdd` | [[app.html]] | **no** | no |
| `window._refreshLiveData` | [[app.html]] | **no** | no |
| `window._resizeNodesByCap` | [[app.html]] | sí | sí (solo pruebas) |
| `window._smGlobe` | [[engine.spacemonitor.js]] | **no** | no |
| `window._wmGlobe` | [[engine.worldmonitor.js]] | **no** | no |
| `window.applyVerifiedValuations` | [[app.html]] | sí | sí (solo pruebas) |
| `window.buildScenarioSeed` | [[sim.scenario_builder.js]] | sí | no |
| `window.closeDiagnostics` | [[app.html]] | **no** | no |
| `window.closePropuestas` | [[app.html]] | **no** | sí (solo pruebas) |
| `window.closeRegistro` | [[app.html]] | **no** | no |
| `window.initCanvasTab` | [[app.html]] | sí | no |
| `window.khJSON` | [[app.html]] | sí | no |
| `window.linkTrust` | [[nodes.merge_graph.js]] | sí | sí (solo pruebas) |
| `window.loadFredMacro` | [[app.html]] | sí | no |
| `window.loadInvestor13F` | [[app.html]] | sí | no |
| `window.loadTradeFlows` | [[app.html]] | sí | no |
| `window.openTradePanelFn` | [[app.html]] | sí | no |
| `window.renderNrsTop10` | [[app.html]] | sí | no |
| `window.settleGraph` | [[app.html]] | sí | sí (solo pruebas) |
| `window.togglePortfolio` | [[app.html]] | **no** | no |
| `window.xrayImpactViaState` | [[engine.xray.js]] | **no** | sí (solo pruebas) |

## Rutas definidas que nadie llama (9)

Posible código muerto: ni la pantalla, ni el servidor, ni las pruebas, ni los scripts nombran la ruta.

| Método | Ruta | Función | Módulo |
|---|---|---|---|
| `GET` | `/api/ontology/graph` | `graph` | [[ontology.api.py]] |
| `GET` | `/api/research/agents` | `agents` | [[research.api.py]] |
| `GET` | `/api/research/budget` | `budget` | [[research.api.py]] |
| `POST` | `/api/research/events` | `events` | [[research.api.py]] |
| `GET` | `/api/tensor/eval` | `tensor_eval` | [[matrix.tensor_api.py]] |
| `GET` | `/api/tensor/status` | `tensor_status` | [[matrix.tensor_api.py]] |
| `GET` | `/api/trade/diag` | `trade_diag` | [[server.py]] |
| `GET` | `/api/vocabulary` | `api_vocabulary` | [[server.py]] |
| `GET` | `/api/vocabulary/unknown` | `api_vocabulary_unknown` | [[server.py]] |

**Solo las llaman las pruebas** (23): `GET /api/ai/debug`, `GET /api/brokerage/audit`, `GET /api/diag/recent`, `GET /api/khipu/tools`, `GET /api/market/providers`, `GET /api/market/quote/<path:symbol>`, `GET /api/matrix/parity`, `GET /api/ontology/agents/brief`, `POST /api/ontology/bulk/import`, `POST /api/ontology/events`, `GET /api/ontology/events/<event_id>`, `GET /api/ontology/search`, `GET /api/ontology/sources`, `POST /api/ops/check`, `GET /api/ops/last_check`, `GET /api/tensor/rank`, `POST /api/tensor/suggest`, `POST /api/trade/agent/config`, `POST /api/voice/adopt`, `GET /api/voice/agent-diag`, `POST /api/voice/agent-tune`, `GET,POST /api/voice/sync-agent`, `GET /api/voice/voices`

## Llamadas a rutas que no existen (0)

Textos con forma de ruta (`/api/…`) en el código que no coinciden con ninguna ruta del servidor. Pueden ser restos de funciones retiradas o rutas armadas por partes.

## Variables leídas en el código que faltan en CLAUDE.md (63)

Se pueden configurar en Railway pero nadie las anotó en la lista de CLAUDE.md.

[[ENV AI_BUSY_WAIT_S]], [[ENV AI_CLAUDE_TIMEOUT_DEEP_S]], [[ENV AI_DAILY_LIMIT_USD]], [[ENV AI_MONTHLY_LIMIT_USD]], [[ENV AI_PER_USER_DAILY_USD]], [[ENV AI_PRICES_JSON]], [[ENV ALPHA_VANTAGE_KEY]], [[ENV ANTHROPIC_ADMIN_KEY]], [[ENV BIXBY_AUTOSYNC]], [[ENV CLAUDE_KEY]], [[ENV CLOUDFLARE_RADAR_TOKEN]], [[ENV COINGECKO_KEY]], [[ENV COMMITTEE_MAX_SEATS]], [[ENV CSP_ENABLED]], [[ENV CSP_REPORT_ONLY]], [[ENV DB_CONNECT_TIMEOUT_S]], [[ENV DB_POOL_TIMEOUT_S]], [[ENV DECIDE_ENABLED]], [[ENV DECIDE_MIN_CONF]], [[ENV DECIDE_WAIT_S]], [[ENV ELEVENLABS_LLM]], [[ENV GEMINI_HOT_S]], [[ENV GEMINI_THINKING]], [[ENV GOOGLE_API_KEY]], [[ENV IMPORT_BULK_WEIGHT_FACTOR]], [[ENV INSIGHTS_INFLIGHT_WAIT_S]], [[ENV INVESTIGADOR_AUTO]], [[ENV INVESTIGADOR_AUTO_CUTOFF_HORAS]], [[ENV KHIPU_URL]], [[ENV LIVE_DEADLINE_S]], [[ENV MATRIX_BUSY_WAIT_S]], [[ENV MATRIX_ENGINE]], [[ENV MCP_MAX_INFLIGHT]], [[ENV MCP_MAX_INFLIGHT_TOTAL]], [[ENV MCP_OAUTH_TTL_HOURS]], [[ENV MCP_PIN_LOCK_MIN]], [[ENV MCP_PIN_MAX_FAILS]], [[ENV MCP_RATE_PER_MIN]], [[ENV MCP_RESEARCH_PER_HOUR]], [[ENV MCP_STATIC_TOKEN]], [[ENV MCP_TRADE_PER_HOUR]], [[ENV MCP_TRUSTED_PROXY_HOPS]], [[ENV NVIDIA_API_KEY]], [[ENV RAILWAY_PUBLIC_DOMAIN]], [[ENV REDIS_URL]], [[ENV RESEARCH_DEDUPE_MINUTES]], [[ENV RESEARCH_HEARTBEAT_STALE_MIN]], [[ENV RESEARCH_MAX_AGENTS_PER_JOB]], [[ENV SEC_USER_AGENT]], [[ENV SMOKE_RETRIES]], [[ENV SPACE_LL2_BASE]], [[ENV TAVILY_KEY]], [[ENV TYPESAFE_API_URL]], [[ENV TYPESAFE_KEY]], [[ENV WORLD_ADVISORIES_URL]], [[ENV WORLD_FEDREG_URL]], [[ENV WORLD_GDACS_URL]], [[ENV WORLD_GDELT_BACKFILL]], [[ENV WORLD_GDELT_EVENTS]], [[ENV WORLD_GDELT_EVENTS_BASE]], [[ENV WORLD_GPR_DAILY_URL]], [[ENV WORLD_GPR_MONTHLY_URL]], [[ENV WORLD_PORTWATCH_URL]]

Solo aparecen en archivos de despliegue (Dockerfile, docker-compose.yml, workflows) y no en CLAUDE.md (2): [[ENV GUNICORN_MAX_REQUESTS_JITTER]], [[ENV OPENAI_KEY]]

Solo aparecen en listas de nombres (p. ej. la lista de secretos que se tapan en los logs) (5): [[ENV ANTHROPIC_API_KEY]], [[ENV RAILWAY_ENVIRONMENT]], [[ENV RAILWAY_ENVIRONMENT_NAME]], [[ENV RAILWAY_PROJECT_ID]], [[ENV TAVILY_API_KEY]]

## Variables de la lista de CLAUDE.md que nadie lee (0)

_Ninguna._

## Scripts que app.html carga pero sw.js no guarda en caché (0)

Regla de CLAUDE.md: todo archivo JS nuevo va también al array SHELL de `sw.js`.

_Ninguno._

## Archivos en la capa "Otros" (0)

Faltan en la tabla de capas (`REGLAS_CAPA` en `scripts/build_vault.py`).

_Ninguno: todo tiene capa._
