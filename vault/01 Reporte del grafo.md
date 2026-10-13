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
| Archivos de código (Python, JS, HTML) | 224 |
| Líneas de código | 132.923 |
| Archivos de datos del catálogo | 28 |
| Archivos de prueba | 197 |
| Documentos | 29 |
| Rutas HTTP | 255 |
| Grupos de API | 61 |
| Herramientas MCP | 32 |
| Variables de entorno | 157 |
| Sesiones de trabajo | 104 |
| Aristas `calls_endpoint` | 700 |
| Aristas `defines_endpoint` | 287 |
| Aristas `imports` | 1.987 |
| Aristas `loads_script` | 83 |
| Aristas `mentions_in_session` | 540 |
| Aristas `reads_env` | 220 |
| Aristas `references_file` | 60 |
| Aristas `tested_by` | 1.454 |
| Aristas `uses_global` | 354 |

## Nodos "dios" (más conectados)

Conexiones de código entre archivos (importa, usa globales, carga, nombra, llama a su ruta). Mucho acoplamiento = cambiar ahí afecta a muchos.

| Archivo | Total | Entran | Salen | Capa |
|---|---|---|---|---|
| [[app.html]] | 147 | 56 | 91 | [[Capa Interfaz (Khipus OS)]] |
| [[server.py]] | 93 | 26 | 67 | [[Capa Infraestructura]] |
| [[ontology.db.py]] | 54 | 45 | 9 | [[Capa Ontología y grafo temporal]] |
| [[engine.cockpit.js]] | 44 | 12 | 32 | [[Capa Interfaz (Khipus OS)]] |
| [[core.governance.py]] | 38 | 33 | 5 | [[Capa Infraestructura]] |
| [[core.__init__.py]] | 37 | 37 | 0 | [[Capa Infraestructura]] |
| [[core.http.py]] | 37 | 35 | 2 | [[Capa Infraestructura]] |
| [[core.decisions.py]] | 36 | 29 | 7 | [[Capa Infraestructura]] |
| [[mcp_server.tools.py]] | 35 | 6 | 29 | [[Capa MCP y API]] |
| [[nodes.nodes_seed.js]] | 35 | 35 | 0 | [[Capa Datos del catálogo]] |
| [[core.khipu_chat.py]] | 32 | 6 | 26 | [[Capa Chat y agentes]] |
| [[core.identity.py]] | 31 | 29 | 2 | [[Capa Infraestructura]] |
| [[ontology.api.py]] | 30 | 8 | 22 | [[Capa Ontología y grafo temporal]] |
| [[research.committee.py]] | 29 | 9 | 20 | [[Capa Comité]] |
| [[ontology.models.py]] | 28 | 25 | 3 | [[Capa Ontología y grafo temporal]] |
| [[engine.resolve.js]] | 27 | 18 | 9 | [[Capa Chat y agentes]] |
| [[engine.voice.js]] | 27 | 4 | 23 | [[Capa Voz]] |
| [[research.committee_api.py]] | 27 | 7 | 20 | [[Capa Comité]] |
| [[core.world.py]] | 26 | 17 | 9 | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] |
| [[research.runner.py]] | 26 | 8 | 18 | [[Capa Investigación]] |

## Módulos sin pruebas (24)

Código (no datos) que ninguna prueba importa ni nombra. Ordenado por tamaño.

| Módulo | Líneas | Capa |
|---|---|---|
| [[engine.worldmonitor.js]] | 1.326 | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] |
| [[engine.universe2d.js]] | 1.048 | [[Capa Interfaz (Khipus OS)]] |
| [[engine.command_center.js]] | 433 | [[Capa Chat y agentes]] |
| [[scripts.ingest_enrichment_md.py]] | 404 | [[Capa Datos del catálogo]] |
| [[engine.orb.js]] | 396 | [[Capa Voz]] |
| [[engine.termdata.js]] | 359 | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] |
| [[scripts.calibrate_kernel.py]] | 355 | [[Capa Cuantitativo (matrices, tensores, riesgo)]] |
| [[scripts.ingest_multicapa.py]] | 343 | [[Capa Datos del catálogo]] |
| [[core.country_geo.py]] | 222 | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] |
| [[engine.matrixview.js]] | 207 | [[Capa Cuantitativo (matrices, tensores, riesgo)]] |
| [[engine.pricehist.js]] | 189 | [[Capa Interfaz (Khipus OS)]] |
| [[security_audit.py]] | 182 | [[Capa Infraestructura]] |
| [[engine.compare.js]] | 168 | [[Capa Cuantitativo (matrices, tensores, riesgo)]] |
| [[research.contradictions.py]] | 143 | [[Capa Investigación]] |
| [[engine.layers.js]] | 132 | [[Capa Interfaz (Khipus OS)]] |
| [[core.providers.coingecko.py]] | 123 | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] |
| [[engine.nav4.js]] | 118 | [[Capa Interfaz (Khipus OS)]] |
| [[scripts.build_instrument_review.py]] | 118 | [[Capa Datos del catálogo]] |
| [[scripts.reconcile_v0_to_ontology.py]] | 104 | [[Capa Ontología y grafo temporal]] |
| [[engine.canvas-data.js]] | 72 | [[Capa Chat y agentes]] |
| [[scripts.build_private_valuations.py]] | 71 | [[Capa Datos del catálogo]] |
| [[scripts.build_listing_status.py]] | 63 | [[Capa Datos del catálogo]] |
| [[scripts.link_origins.js]] | 56 | [[Capa Ontología y grafo temporal]] |
| [[core.decide_api.py]] | 25 | [[Capa Chat y agentes]] |

## Módulos Python que nadie importa (0)

_Ninguno._

## Globales window.* que ningún otro archivo usa (29)

Se exportan a `window` pero nadie más las lee. Si "se usa dentro de su archivo" dice sí, la función sí trabaja (solo sobra la exportación); si dice no, es candidata a código muerto.

| Global | Definida en | ¿Se usa dentro de su archivo? | ¿La nombra alguna prueba? |
|---|---|---|---|
| `window.APP_NAME` | [[app.html]] | **no** | no |
| `window.ASSISTANT_NAME` | [[app.html]] | **no** | no |
| `window.DESC_FILL` | [[nodes.meta_fill.js]] | sí | no |
| `window.KhipuLiveCaps` | [[app.html]] | **no** | no |
| `window.KhipuLiveFund` | [[app.html]] | **no** | no |
| `window.KhipuVoiceAudio` | [[engine.voice.js]] | **no** | sí (solo pruebas) |
| `window.META_CHINA` | [[nodes.nodes_china.js]] | sí | no |
| `window.META_FILL` | [[nodes.meta_fill.js]] | sí | no |
| `window.OntologyAlerts` | [[app.html]] | sí | no |
| `window._briefAutoAllowed` | [[engine.brief.js]] | **no** | sí (solo pruebas) |
| `window._buildNrsDegree` | [[app.html]] | sí | sí (solo pruebas) |
| `window._lblOn` | [[app.html]] | sí | sí (solo pruebas) |
| `window._mapState` | [[app.html]] | **no** | sí (solo pruebas) |
| `window._resizeNodesByCap` | [[app.html]] | sí | sí (solo pruebas) |
| `window._smGlobe` | [[engine.spacemonitor.js]] | **no** | no |
| `window._wmGlobe` | [[engine.worldmonitor.js]] | **no** | no |
| `window.applyVerifiedValuations` | [[app.html]] | sí | sí (solo pruebas) |
| `window.buildScenarioSeed` | [[sim.scenario_builder.js]] | sí | no |
| `window.closePropuestas` | [[app.html]] | **no** | sí (solo pruebas) |
| `window.initCanvasTab` | [[app.html]] | sí | no |
| `window.khJSON` | [[app.html]] | sí | no |
| `window.linkTrust` | [[nodes.merge_graph.js]] | sí | sí (solo pruebas) |
| `window.loadFredMacro` | [[app.html]] | sí | no |
| `window.loadInvestor13F` | [[app.html]] | sí | no |
| `window.loadTradeFlows` | [[app.html]] | sí | no |
| `window.openTradePanelFn` | [[app.html]] | sí | no |
| `window.renderNrsTop10` | [[app.html]] | sí | no |
| `window.settleGraph` | [[app.html]] | sí | sí (solo pruebas) |
| `window.xrayImpact` | [[engine.xray.js]] | **no** | sí (solo pruebas) |

## Rutas definidas que nadie llama (9)

Posible código muerto: ni la pantalla, ni el servidor, ni las pruebas, ni los scripts nombran la ruta.

| Método | Ruta | Función | Módulo |
|---|---|---|---|
| `GET` | `/api/ontology/gates` | `gates_status` | [[ontology.api.py]] |
| `GET` | `/api/prices/eod/<path:symbol>` | `prices_eod` | [[core.prices_api.py]] |
| `GET` | `/api/research/agents` | `agents` | [[research.api.py]] |
| `GET` | `/api/research/budget` | `budget` | [[research.api.py]] |
| `POST` | `/api/research/events` | `events` | [[research.api.py]] |
| `GET` | `/api/tensor/eval` | `tensor_eval` | [[matrix.tensor_api.py]] |
| `GET` | `/api/tensor/status` | `tensor_status` | [[matrix.tensor_api.py]] |
| `GET` | `/api/trade/diag` | `trade_diag` | [[server.py]] |
| `GET` | `/api/vocabulary/unknown` | `api_vocabulary_unknown` | [[server.py]] |

**Solo las llaman las pruebas** (34): `GET /api/ai/debug`, `GET /api/brokerage/audit`, `GET /api/diag/recent`, `GET /api/governance/active`, `GET /api/governance/attribution`, `GET /api/instruments/review`, `GET /api/khipu/tools`, `GET /api/ledger/chain`, `POST /api/ledger/chain_ack`, `GET /api/ledger/decision/<decision_id>`, `GET /api/ledger/decisions`, `GET /api/ledger/status`, `GET /api/ledger/verify`, `GET /api/market/providers`, `GET /api/market/quote/<path:symbol>`, `GET /api/matrix/metrics`, `GET /api/matrix/parity`, `GET /api/ontology/agents/brief`, `POST /api/ontology/bulk/import`, `POST /api/ontology/events`, `GET /api/ontology/events/<event_id>`, `GET /api/ontology/search`, `GET /api/ontology/sources`, `POST /api/ops/check`, `GET /api/ops/last_check`, `GET /api/tensor/rank`, `POST /api/tensor/suggest`, `POST /api/trade/agent/config`, `GET /api/vocabulary`, `POST /api/voice/adopt`, `GET /api/voice/agent-diag`, `POST /api/voice/agent-tune`, `GET,POST /api/voice/sync-agent`, `GET /api/voice/voices`

## Llamadas a rutas que no existen (10)

Textos con forma de ruta (`/api/…`) en el código que no coinciden con ninguna ruta del servidor. Pueden ser restos de funciones retiradas o rutas armadas por partes.

| Archivo | Ruta nombrada |
|---|---|
| [[core.replay.py]] | `/api/hot/scenario` |
| [[core.replay.py]] | `/api/hot/scenario_pnl` |
| [[engine.hotclient.js]] | `/api/hot/card/` |
| [[engine.hotclient.js]] | `/api/hot/chokepoints` |
| [[engine.hotclient.js]] | `/api/hot/factors` |
| [[engine.hotclient.js]] | `/api/hot/impact/` |
| [[engine.hotclient.js]] | `/api/hot/nrs` |
| [[engine.hotclient.js]] | `/api/hot/scenario` |
| [[engine.hotclient.js]] | `/api/hot/scenario_pnl` |
| [[engine.hotclient.js]] | `/api/hot/status` |

## Variables leídas en el código que faltan en CLAUDE.md (0)

Se pueden configurar en Railway pero nadie las anotó en la lista de CLAUDE.md.

_Ninguna._

## Variables de la lista de CLAUDE.md que nadie lee (7)

`BROKERAGE_APPROVAL_TTL_MIN`, `HOTVIEWS_COALESCE_S`, `HOTVIEWS_LISTEN`, `KERNEL_PARAMS`, `KHIPU_GATES`, `RESEARCH_CALIBRATION_K`, `RESEARCH_OUTCOME_BAND`

## Scripts que app.html carga pero sw.js no guarda en caché (0)

Regla de CLAUDE.md: todo archivo JS nuevo va también al array SHELL de `sw.js`.

_Ninguno._

## Archivos en la capa "Otros" (0)

Faltan en la tabla de capas (`REGLAS_CAPA` en `scripts/build_vault.py`).

_Ninguno: todo tiene capa._
