---
tipo: "capa"
capa: "Interfaz (Khipus OS)"
archivos: 31
tags: ["capa/interfaz", "tipo/capa"]
---

# Capa Interfaz (Khipus OS)

> Lo que ves en pantalla: la Cabina / Khipus OS, ventanas, pestañas, mapa, avisos y estilos.

**31 archivos · 30.151 líneas.** Volver al [[00 Mapa de Khipus]].

## Archivos

- [[engine.cockpit.js]] — 5.048 líneas · CABINA DE BIXBY · el modo pantalla completa Khipu deja de ser un botón: SE VUELVE la pantalla. - Arriba: el orbe/logo de Khipu + estado (escuchando / …
- [[engine.app_main.js]] — 4.850 líneas · Global error reporter — shows uncaught JS errors on screen (no devtools needed)
- [[app.html]] — 3.566 líneas
- [[engine.app_coordinator.js]] — 2.718 líneas · Khipu Core Coordinator
- [[engine.oswindows.js]] — 1.646 líneas · VENTANAS NATIVAS de Khipus OS (2026-10-06)
- [[engine.genui.js]] — 1.435 líneas · RESPUESTAS VISUALES del chat (kblocks/1): docs/CHAT_UI_GENERATIVA.md §7. Dibuja; NUNCA calcula cifras. DOM seguro, 17 tipos, acciones solo …
- [[engine.graph3d.js]] — 1.227 líneas · Motor de visualización 3D Three.js para Khipu Finance Renderiza los 450+ nodos como esferas en el espacio, con tamaño por market cap, links de …
- [[engine.desktop.js]] — 1.161 líneas · ESCRITORIO KHIPU (K1, 2026-10-04)
- [[engine.universe2d.js]] — 1.059 líneas · Universo 2D: respaldo TOTAL del mapa 3D sin WebGL.
- [[engine.importer.js]] — 935 líneas · EXPANSION_5K E2.7 · 🩺 Sistema → Diagnóstico → «📥 Importar empresas». Panel de la tubería de importación (ontology/company_import.py, rutas …
- [[engine.toast.js]] — 767 líneas · NOTIFICACIONES y CONFIRMACIÓN de órdenes (pedido de Fabrizio 2026-10-02: "que te avise cuando estás comprando con una notificación pop up o …
- [[engine.genui_charts.js]] — 739 líneas · GRÁFICOS de las respuestas visuales (kblocks/1, docs/CHAT_UI_GENERATIVA.md §7.2). Portados del Canvas (_cvLine/_cvBar) a tokens --os-\* y a CUALQUIER …
- [[engine.xray.js]] — 669 líneas · X-RAY DE EMPRESA · "desarmar el alma" (Etapa 4, wow #1) Overlay NEXUS-styled que abre para cualquier nodo: - anatomía (sector, país, precio en vivo, …
- [[engine.governance.js]] — 538 líneas · 🩺 Sistema → Gobernanza (INFRA_OPERATIVA paso 12; pieza mínima del paso 25). Muestra el RELEASE vigente (reglas y números versionados), «Ratificar …
- [[engine.catalog_sync.js]] — 440 líneas · EXPANSION_5K E3.1 (lote L, 2026-10-15): el catálogo del navegador se COMPLETA con lo que solo está en Postgres.
- [[engine.explain.js]] — 419 líneas · EXPLICADOR DE MÉTRICAS para no expertos (2026-07-12). Feedback real: un inversionista preguntó "¿qué es el NRS y cómo se calcula?" y la app no se lo …
- [[engine.pfstore.js]] — 387 líneas · UN SOLO LUGAR DONDE SE GUARDAN TUS POSICIONES
- [[engine.audit.js]] — 297 líneas · 🩺 Sistema → 📋 Registro → ⚖ Auditoría (INFRA_OPERATIVA paso 24, §5.6). Lista las decisiones recientes del LIBRO (filtros: tipo, quién, fecha) y por …
- [[engine.app_scatter.js]] — 281 líneas · KHIPU FINANCE — Scatter 3D Semántico con Medidores Botón 📊: posiciona empresas en ejes semánticos + panel de medidores interactivo
- [[engine.guide.js]] — 271 líneas · pestaña "❓ Guía": explica la app en lenguaje simple. Sin jerga técnica. Expone window.initGuiaTab (mismo patrón que initTKGTab). Actualizada …
- [[engine.genui_shapes.js]] — 237 líneas · FORMAS, IMÁGENES y MINI-MAPA de las respuestas visuales (kblocks/1, docs/CHAT_UI_GENERATIVA.md §4.6 y §7.2).
- [[engine.simreport.js]] — 230 líneas · INFORME DE ESCENARIO (2026-10-21, «que parezca un producto») Pinta la salida de POST /api/sim/agents (core/sim_agents + core/sim_report) como un …
- [[engine.genui_progress.js]] — 198 líneas · RESPUESTAS VISUALES PROGRESIVAS (F3, docs/CHAT_UI_GENERATIVA.md §6): el motor del chat que pinta los bloques provisionales y hace ATERRIZAR la …
- [[engine.pricehist.js]] — 189 líneas · 🩺 Sistema → «Historia de precios» (BRECHAS bloque 2: la memoria de los números). Muestra cuánta historia guarda Khipus (cierres diarios ajustados, …
- [[engine.signals.js]] — 172 líneas · «1 TOQUE»: señales del agente de trading listas para aprobar (2026-10-20) El agente en modo MANUAL propone (servidor: core/trading_agent.py, GET …
- [[engine.loading.js]] — 159 líneas · Sistema de animaciones de carga por NIVEL DE ESPERA. Pedido de Fabrizio (2026-07-14): "que todo lo que tarde tenga una animación de carga adecuada; …
- [[engine.mascot.js]] — 136 líneas · MASCOTAS BURBUJA de Khipus OS (2026-10-06)
- [[engine.layers.js]] — 132 líneas · SISTEMA DE CAPAS DEL MAPA (petición día 1 de Fabrizio) El mapa deja de ser "todo o nada": enciendes/apagas información como capas. Cada capa = un …
- [[engine.nav4.js]] — 118 líneas · NAVEGACIÓN DE 4 PESTAÑAS (simplificación pedida por Fabrizio) Las 10 pestañas se agrupan bajo 4 primarias: 🗺️ Mapa → map · geo · space · tkg · …
- [[engine.agents_registry.js]] — 79 líneas · EL registro de agentes de Khipus (limpieza 2026-10-11)
- [[engine.tour_script.js]] — 48 líneas · EL guion del recorrido de un minuto (voz para Khipus OS, 2026-10-11)

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| usa a | [[Capa Datos del catálogo]] | 53 |
| la usa | [[Capa Chat y agentes]] | 28 |
| la usa | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 25 |
| usa a | [[Capa Chat y agentes]] | 25 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 23 |
| la usa | [[Capa Dinero (carteras, trading, corretaje)]] | 20 |
| usa a | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 18 |
| la usa | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 14 |
| usa a | [[Capa Ontología y grafo temporal]] | 14 |
| la usa | [[Capa Ontología y grafo temporal]] | 13 |
| usa a | [[Capa Dinero (carteras, trading, corretaje)]] | 13 |
| usa a | [[Capa Infraestructura]] | 13 |
| la usa | [[Capa Comité]] | 10 |
| la usa | [[Capa Voz]] | 10 |
| usa a | [[Capa Comité]] | 7 |
| la usa | [[Capa Infraestructura]] | 6 |
| usa a | [[Capa Investigación]] | 6 |
| usa a | [[Capa Voz]] | 5 |
| la usa | [[Capa Investigación]] | 4 |
| la usa | [[Capa MCP y API]] | 4 |
| usa a | [[Capa MCP y API]] | 3 |
| la usa | [[Capa Datos del catálogo]] | 1 |
