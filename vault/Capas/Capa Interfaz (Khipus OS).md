---
tipo: "capa"
capa: "Interfaz (Khipus OS)"
archivos: 16
tags: ["capa/interfaz", "tipo/capa"]
---

# Capa Interfaz (Khipus OS)

> Lo que ves en pantalla: la Cabina / Khipus OS, ventanas, pestañas, mapa, avisos y estilos.

**16 archivos · 25.226 líneas.** Volver al [[00 Mapa de Khipus]].

## Archivos

- [[app.html]] — 12.665 líneas
- [[engine.cockpit.js]] — 4.983 líneas · CABINA DE BIXBY · el modo pantalla completa Khipu deja de ser un botón: SE VUELVE la pantalla. - Arriba: el orbe/logo de Khipu + estado (escuchando / …
- [[engine.oswindows.js]] — 1.506 líneas · VENTANAS NATIVAS de Khipus OS (2026-10-06)
- [[engine.graph3d.js]] — 1.216 líneas · Motor de visualización 3D Three.js para Khipu Finance Renderiza los 450+ nodos como esferas en el espacio, con tamaño por market cap, links de …
- [[engine.desktop.js]] — 1.161 líneas · ESCRITORIO KHIPU (K1, 2026-10-04)
- [[engine.universe2d.js]] — 1.048 líneas · Universo 2D: respaldo TOTAL del mapa 3D sin WebGL.
- [[engine.toast.js]] — 767 líneas · NOTIFICACIONES y CONFIRMACIÓN de órdenes (pedido de Fabrizio 2026-10-02: "que te avise cuando estás comprando con una notificación pop up o …
- [[engine.xray.js]] — 710 líneas · X-RAY DE EMPRESA · "desarmar el alma" (Etapa 4, wow #1) Overlay NEXUS-styled que abre para cualquier nodo: - anatomía (sector, país, precio en vivo, …
- [[engine.guide.js]] — 271 líneas · pestaña "❓ Guía": explica la app en lenguaje simple. Sin jerga técnica. Expone window.initGuiaTab (mismo patrón que initTKGTab). Actualizada …
- [[engine.explain.js]] — 227 líneas · EXPLICADOR DE MÉTRICAS para no expertos (2026-07-12). Feedback real: un inversionista preguntó "¿qué es el NRS y cómo se calcula?" y la app no se lo …
- [[engine.loading.js]] — 159 líneas · Sistema de animaciones de carga por NIVEL DE ESPERA. Pedido de Fabrizio (2026-07-14): "que todo lo que tarde tenga una animación de carga adecuada; …
- [[engine.mascot.js]] — 136 líneas · MASCOTAS BURBUJA de Khipus OS (2026-10-06)
- [[engine.layers.js]] — 133 líneas · SISTEMA DE CAPAS DEL MAPA (petición día 1 de Fabrizio) El mapa deja de ser "todo o nada": enciendes/apagas información como capas. Cada capa = un …
- [[engine.nav4.js]] — 118 líneas · NAVEGACIÓN DE 4 PESTAÑAS (simplificación pedida por Fabrizio) Las 10 pestañas se agrupan bajo 4 primarias: 🗺️ Mapa → map · geo · space · tkg · …
- [[engine.agents_registry.js]] — 78 líneas · EL registro de agentes de Khipus (limpieza 2026-10-11)
- [[engine.tour_script.js]] — 48 líneas · EL guion del recorrido de un minuto (voz para Khipus OS, 2026-10-11)

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| usa a | [[Capa Datos del catálogo]] | 31 |
| la usa | [[Capa Chat y agentes]] | 20 |
| la usa | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 20 |
| usa a | [[Capa Chat y agentes]] | 16 |
| usa a | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 16 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 14 |
| la usa | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 11 |
| la usa | [[Capa Dinero (carteras, trading, corretaje)]] | 11 |
| la usa | [[Capa Ontología y grafo temporal]] | 9 |
| usa a | [[Capa Ontología y grafo temporal]] | 9 |
| la usa | [[Capa Comité]] | 8 |
| la usa | [[Capa Voz]] | 8 |
| usa a | [[Capa Comité]] | 6 |
| usa a | [[Capa Dinero (carteras, trading, corretaje)]] | 6 |
| usa a | [[Capa Infraestructura]] | 6 |
| la usa | [[Capa Infraestructura]] | 5 |
| la usa | [[Capa Investigación]] | 4 |
| usa a | [[Capa Investigación]] | 4 |
| usa a | [[Capa Voz]] | 4 |
| la usa | [[Capa MCP y API]] | 3 |
| usa a | [[Capa MCP y API]] | 2 |
