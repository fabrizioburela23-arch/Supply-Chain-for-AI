---
tipo: "modulo"
capa: "Infraestructura"
ruta: "sw.js"
lenguaje: "javascript"
lineas: 296
aliases: ["sw.js"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# sw.js

> Módulo · capa [[Capa Infraestructura]] · 296 líneas · `sw.js`

## Para qué sirve

Khipu Finance — Service Worker Servido por server.py en /sw.js con cabecera Service-Worker-Allowed: / CACHE va en la línea 6 (regla de despliegue #1: bump vN → vN+1 en cada cambio de JS/HTML). server.py (_sw_version) lee SOLO los primeros 2048 caracteres para inyectar ?v=N en los &lt;script src> — no la bajes.

## API pública (globales que define)

`window.__KHIPU_STALE_SHELL`

De nivel superior (globales del script): `API_RE`, `CACHE`, `CDN_HOSTS`, `DEGRADED_MS`, `NAV_TIMEOUT_MS`, `SEC_HEADERS`, `SHELL`, `SHELL_KEY`, `STATIC_TIMEOUT_MS`, `VER`, `cacheable`, `cdnCacheable`, `degraded`, `degradedUntil`, `handleApi`, `handleCdn`, `handleNavigate`, `handleStatic`, `isAppShellPath`, `isJSON`, `offlineJSON`, `offlinePage`, `precacheUrl`, `put`, `shellCanBoot`, `staleShell`

## Depende de

_Nada interno._

## Lo usan

- [[core.ops_check.py]] — lo nombra por su ruta
- [[engine.app_main.js]] — lo nombra por su ruta
- [[engine.live.js]] — lo nombra por su ruta
- [[server.py]] — lo nombra por su ruta

## Pruebas que lo cubren

- [[tests.test_agents_registry.py]]
- [[tests.test_app_split.py]]
- [[tests.test_cleanup_client.py]]
- [[tests.test_client_hardening.py]]
- [[tests.test_csp_estricta.py]]
- [[tests.test_genui_client_static.py]]
- [[tests.test_genui_f3_client_static.py]]
- [[tests.test_khipus_os_integration.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_one_portfolio_store.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_server_smoke.py]]
- [[tests.test_sim_report.py]]
- [[tests.test_voice_tour.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (m) — app.html PARTIDO + 2 arreglos visibles — sw v268]]
- [[Sesión 2026-10-13 (l) — APP.HTML PARTIDO SIN CAMBIAR NADA (G5-06) — sw v267]]
- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
- [[Sesión 2026-10-09 — EL COMITÉ ENTRA A KHIPUS OS (sw v250)]]
- [[Sesión 2026-07-03 — Etapa 0 — Seguridad y cimientos - CÓDIGO COMPLETO]]
- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
- [[Sesión 2026-07-12 — Etapa H — Feedback 7 - explicabilidad + regla bilingüe + cripto]]

## Caché del service worker

Versión de caché actual: `khipu-finance-v288` — se sube en CADA cambio de JS/HTML (regla de despliegue n.º 1 de CLAUDE.md).

El array SHELL guarda **108** archivos para usarlos sin conexión (lista en texto para no saturar el grafo):

`app.html`, `engine/agents_registry.js`, `engine/aispend.js`, `engine/app_canvas.js`, `engine/app_coordinator.js`, `engine/app_main.js`, `engine/app_preflight.js`, `engine/app_scatter.js`, `engine/app_trade_panel.js`, `engine/audit.js`, `engine/brief.js`, `engine/canvas-data.js`, `engine/catalog_sync.js`, `engine/clients.js`, `engine/cockpit.js`, `engine/command_center.js`, `engine/committee.js`, `engine/compare.js`, `engine/crypto.js`, `engine/desktop.js`, `engine/explain.js`, `engine/fincard.js`, `engine/genui.js`, `engine/genui_charts.js`, `engine/genui_progress.js`, `engine/genui_shapes.js`, `engine/geo_coords.js`, `engine/globe.js`, `engine/governance.js`, `engine/graph3d.js`, `engine/guide.js`, `engine/hotclient.js`, `engine/hypergraph.js`, `engine/importer.js`, `engine/insights.js`, `engine/khipu_chat.js`, `engine/khipu_lang.js`, `engine/layers.js`, `engine/live.js`, `engine/livesim.js`, `engine/loading.js`, `engine/localcharts.js`, `engine/maptime.js`, `engine/mascot.js`, `engine/matrixview.js`, `engine/mcpconnect.js`, `engine/nav4.js`, `engine/orb.js`, `engine/oswindows.js`, `engine/pfcommittee.js`, `engine/pfreports.js`, `engine/pfstore.js`, `engine/pickers.js`, `engine/portfolios.js`, `engine/pricehist.js`, `engine/reconcile.js`, `engine/research.js`, `engine/resolve.js`, `engine/riskreport.js`, `engine/secondbrain.js`, `engine/signals.js`, `engine/simreport.js`, `engine/spacemonitor.js`, `engine/statematrix.js`, `engine/sync.js`, `engine/temporal-graph.js`, `engine/termdata.js`, `engine/timeline3d.js`, `engine/toast.js`, `engine/tour_script.js`, `engine/trade.js`, `engine/universe2d.js`, `engine/voice.js`, `engine/worldmonitor.js`, `engine/xray.js`, `index.html`, `nodes/categories_extra.js`, `nodes/crypto_intel.js`, `nodes/crypto_intel2.js`, `nodes/legal_names.js`, `nodes/links_all.js`, `nodes/links_connect.js`, `nodes/links_expand.js`, `nodes/listing_status.js`, `nodes/merge_graph.js`, `nodes/meta_fill.js`, `nodes/nodes_china.js`, `nodes/nodes_expand.js`, `nodes/nodes_expand2.js`, `nodes/nodes_expand3.js`, `nodes/nodes_expand4.js`, `nodes/nodes_expand5.js`, `nodes/nodes_multicapa.js`, `nodes/nodes_nuclear.js`, `nodes/nodes_seed.js`, `nodes/nodes_spacex.js`, `nodes/ontology.js`, `nodes/ontology_facts.js`, `nodes/preipo_intel.js`, `nodes/private_valuations.js`, `nodes/temporal_seed_facts.js`, `nodes/temporal_seed_facts2.js`, `sim/scenario_builder.js`, `sw.js`, `vendor/chart.umd.min.js`, `vendor/d3.min.js`, `vendor/satellite.min.js`, `vendor/three.min.js`
