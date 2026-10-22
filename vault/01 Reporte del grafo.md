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
| Archivos de código (Python, JS, HTML) | 252 |
| Líneas de código | 150.709 |
| Archivos de datos del catálogo | 30 |
| Archivos de prueba | 264 |
| Documentos | 32 |
| Rutas HTTP | 266 |
| Grupos de API | 61 |
| Herramientas MCP | 34 |
| Variables de entorno | 158 |
| Sesiones de trabajo | 113 |
| Aristas `calls_endpoint` | 781 |
| Aristas `defines_endpoint` | 300 |
| Aristas `imports` | 2.372 |
| Aristas `loads_script` | 95 |
| Aristas `mentions_in_session` | 602 |
| Aristas `reads_env` | 226 |
| Aristas `references_file` | 71 |
| Aristas `tested_by` | 1.865 |
| Aristas `uses_global` | 468 |

## Nodos "dios" (más conectados)

Conexiones de código entre archivos (importa, usa globales, carga, nombra, llama a su ruta). Mucho acoplamiento = cambiar ahí afecta a muchos.

| Archivo | Total | Entran | Salen | Capa |
|---|---|---|---|---|
| [[app.html]] | 124 | 28 | 96 | [[Capa Interfaz (Khipus OS)]] |
| [[engine.app_main.js]] | 113 | 66 | 47 | [[Capa Interfaz (Khipus OS)]] |
| [[server.py]] | 99 | 31 | 68 | [[Capa Infraestructura]] |
| [[ontology.db.py]] | 58 | 48 | 10 | [[Capa Ontología y grafo temporal]] |
| [[engine.cockpit.js]] | 52 | 14 | 38 | [[Capa Interfaz (Khipus OS)]] |
| [[nodes.nodes_seed.js]] | 44 | 43 | 1 | [[Capa Datos del catálogo]] |
| [[core.governance.py]] | 41 | 36 | 5 | [[Capa Infraestructura]] |
| [[core.__init__.py]] | 40 | 40 | 0 | [[Capa Infraestructura]] |
| [[core.decisions.py]] | 38 | 31 | 7 | [[Capa Infraestructura]] |
| [[core.http.py]] | 37 | 35 | 2 | [[Capa Infraestructura]] |
| [[mcp_server.tools.py]] | 36 | 7 | 29 | [[Capa MCP y API]] |
| [[ontology.api.py]] | 36 | 11 | 25 | [[Capa Ontología y grafo temporal]] |
| [[engine.app_coordinator.js]] | 35 | 16 | 19 | [[Capa Interfaz (Khipus OS)]] |
| [[core.khipu_chat.py]] | 34 | 6 | 28 | [[Capa Chat y agentes]] |
| [[engine.resolve.js]] | 33 | 21 | 12 | [[Capa Chat y agentes]] |
| [[core.identity.py]] | 32 | 30 | 2 | [[Capa Infraestructura]] |
| [[ontology.models.py]] | 32 | 28 | 4 | [[Capa Ontología y grafo temporal]] |
| [[core.world.py]] | 31 | 21 | 10 | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] |
| [[engine.toast.js]] | 30 | 27 | 3 | [[Capa Interfaz (Khipus OS)]] |
| [[engine.voice.js]] | 30 | 4 | 26 | [[Capa Voz]] |

## Módulos sin pruebas (22)

Código (no datos) que ninguna prueba importa ni nombra. Ordenado por tamaño.

| Módulo | Líneas | Capa |
|---|---|---|
| [[engine.worldmonitor.js]] | 1.326 | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] |
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
| [[scripts.build_instrument_review.py]] | 119 | [[Capa Datos del catálogo]] |
| [[engine.nav4.js]] | 118 | [[Capa Interfaz (Khipus OS)]] |
| [[scripts.reconcile_v0_to_ontology.py]] | 104 | [[Capa Ontología y grafo temporal]] |
| [[engine.canvas-data.js]] | 72 | [[Capa Chat y agentes]] |
| [[scripts.build_private_valuations.py]] | 71 | [[Capa Datos del catálogo]] |
| [[scripts.build_listing_status.py]] | 63 | [[Capa Datos del catálogo]] |
| [[scripts.link_origins.js]] | 56 | [[Capa Ontología y grafo temporal]] |

## Módulos Python que nadie importa (0)

_Ninguno._

## Globales window.* que ningún otro archivo usa (23)

Se exportan a `window` pero nadie más las lee. Si "se usa dentro de su archivo" dice sí, la función sí trabaja (solo sobra la exportación); si dice no, es candidata a código muerto.

| Global | Definida en | ¿Se usa dentro de su archivo? | ¿La nombra alguna prueba? |
|---|---|---|---|
| `window.APP_NAME` | [[engine.app_main.js]] | **no** | no |
| `window.ASSISTANT_NAME` | [[engine.app_main.js]] | **no** | no |
| `window.DESC_FILL` | [[nodes.meta_fill.js]] | sí | no |
| `window.KhipuLiveCaps` | [[engine.app_main.js]] | **no** | no |
| `window.KhipuVoiceAudio` | [[engine.voice.js]] | **no** | sí (solo pruebas) |
| `window.META_CHINA` | [[nodes.nodes_china.js]] | sí | no |
| `window.META_FILL` | [[nodes.meta_fill.js]] | sí | no |
| `window.OntologyAlerts` | [[engine.app_main.js]] | sí | no |
| `window._briefAutoAllowed` | [[engine.brief.js]] | **no** | sí (solo pruebas) |
| `window._briefPfCard` | [[engine.brief.js]] | **no** | sí (solo pruebas) |
| `window._buildNrsDegree` | [[engine.app_main.js]] | sí | sí (solo pruebas) |
| `window._smGlobe` | [[engine.spacemonitor.js]] | **no** | no |
| `window._wmGlobe` | [[engine.worldmonitor.js]] | **no** | no |
| `window.applyVerifiedValuations` | [[engine.app_main.js]] | sí | sí (solo pruebas) |
| `window.buildScenarioSeed` | [[sim.scenario_builder.js]] | sí | no |
| `window.closePropuestas` | [[engine.app_main.js]] | **no** | sí (solo pruebas) |
| `window.linkTrust` | [[nodes.merge_graph.js]] | sí | sí (solo pruebas) |
| `window.loadFredMacro` | [[engine.app_coordinator.js]] | sí | no |
| `window.loadInvestor13F` | [[engine.app_coordinator.js]] | sí | no |
| `window.loadTradeFlows` | [[engine.app_coordinator.js]] | sí | no |
| `window.openTradePanelFn` | [[engine.app_trade_panel.js]] | sí | no |
| `window.settleGraph` | [[engine.app_main.js]] | sí | sí (solo pruebas) |
| `window.xrayImpact` | [[engine.xray.js]] | **no** | sí (solo pruebas) |

## Rutas definidas que nadie llama (7)

Posible código muerto: ni la pantalla, ni el servidor, ni las pruebas, ni los scripts nombran la ruta.

| Método | Ruta | Función | Módulo |
|---|---|---|---|
| `GET` | `/api/ontology/gates` | `gates_status` | [[ontology.api.py]] |
| `GET` | `/api/prices/eod/<path:symbol>` | `prices_eod` | [[core.prices_api.py]] |
| `GET` | `/api/research/agents` | `agents` | [[research.api.py]] |
| `GET` | `/api/research/budget` | `budget` | [[research.api.py]] |
| `POST` | `/api/research/events` | `events` | [[research.api.py]] |
| `GET` | `/api/trade/diag` | `trade_diag` | [[server.py]] |
| `GET` | `/api/vocabulary/unknown` | `api_vocabulary_unknown` | [[server.py]] |

**Solo las llaman las pruebas** (35): `GET /api/ai/debug`, `GET /api/brokerage/audit`, `GET /api/diag/recent`, `GET /api/governance/active`, `GET /api/governance/attribution`, `GET /api/instruments/review`, `GET /api/khipu/tools`, `GET /api/ledger/chain`, `POST /api/ledger/chain_ack`, `GET /api/ledger/decision/<decision_id>`, `GET /api/ledger/decisions`, `GET /api/ledger/status`, `GET /api/ledger/verify`, `GET /api/market/providers`, `GET /api/market/quote/<path:symbol>`, `GET /api/matrix/metrics`, `GET /api/matrix/parity`, `GET /api/ontology/agents/brief`, `POST /api/ontology/bulk/import`, `POST /api/ontology/events`, `GET /api/ontology/events/<event_id>`, `GET /api/ontology/search`, `GET /api/ontology/sources`, `POST /api/ops/check`, `GET /api/ops/last_check`, `GET /api/tensor/eval`, `GET /api/tensor/rank`, `GET /api/tensor/status`, `POST /api/tensor/suggest`, `GET /api/vocabulary`, `POST /api/voice/adopt`, `GET /api/voice/agent-diag`, `POST /api/voice/agent-tune`, `GET,POST /api/voice/sync-agent`, `GET /api/voice/voices`

## Llamadas a rutas que no existen (14)

Textos con forma de ruta (`/api/…`) en el código que no coinciden con ninguna ruta del servidor. Pueden ser restos de funciones retiradas o rutas armadas por partes.

| Archivo | Ruta nombrada |
|---|---|
| [[core.replay.py]] | `/api/hot/scenario` |
| [[core.replay.py]] | `/api/hot/scenario_pnl` |
| [[engine.catalog_sync.js]] | `/api/hot/catalog` |
| [[engine.catalog_sync.js]] | `/api/hot/catalog/detail` |
| [[engine.genui.js]] | `/api/genui/block` |
| [[engine.hotclient.js]] | `/api/hot/card/` |
| [[engine.hotclient.js]] | `/api/hot/chokepoints` |
| [[engine.hotclient.js]] | `/api/hot/factors` |
| [[engine.hotclient.js]] | `/api/hot/impact/` |
| [[engine.hotclient.js]] | `/api/hot/nrs` |
| [[engine.hotclient.js]] | `/api/hot/scenario` |
| [[engine.hotclient.js]] | `/api/hot/scenario_pnl` |
| [[engine.hotclient.js]] | `/api/hot/status` |
| [[engine.oswindows.js]] | `/api/hot/quote` |

## Variables leídas en el código que faltan en CLAUDE.md (0)

Se pueden configurar en Railway pero nadie las anotó en la lista de CLAUDE.md.

_Ninguna._

## Variables de la lista de CLAUDE.md que nadie lee (7)

`BROKERAGE_APPROVAL_TTL_MIN`, `HOTVIEWS_COALESCE_S`, `KERNEL_PARAMS`, `KHIPU_GATES`, `KH_SCALE`, `RESEARCH_CALIBRATION_K`, `RESEARCH_OUTCOME_BAND`

## Scripts que app.html carga pero sw.js no guarda en caché (0)

Regla de CLAUDE.md: todo archivo JS nuevo va también al array SHELL de `sw.js`.

_Ninguno._

## Archivos en la capa "Otros" (1)

Faltan en la tabla de capas (`REGLAS_CAPA` en `scripts/build_vault.py`).

[[scripts.research_batch.py]]
