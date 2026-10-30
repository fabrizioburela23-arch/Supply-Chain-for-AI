---
tipo: "inicio"
tags: ["tipo/inicio"]
---

# 00 Mapa de Khipus

Bienvenido. Esta bóveda es un **mapa vivo del código de Khipus Finance AI**: cada archivo, ruta de la API, variable de entorno y sesión de trabajo es una nota, y los enlaces entre notas son las conexiones reales del código. La genera `scripts/build_vault.py` sin IA, leyendo el repositorio.

**254 archivos de código (151.331 líneas) · 266 rutas HTTP · 34 herramientas MCP · 158 variables de entorno · 113 sesiones de trabajo.**

Empieza por [[02 Cómo usar esta bóveda]] y mira las cosas sueltas en [[01 Reporte del grafo]].

## Cómo fluye todo

1. **Lo que ves**: [[app.html]] arranca Khipus OS ([[engine.cockpit.js]], [[engine.desktop.js]], [[engine.oswindows.js]]).
2. **El chat**: [[engine.khipu_chat.js]] → `POST /api/khipu/chat` → [[core.khipu_chat.py]], que usa las herramientas de [[mcp_server.tools.py]] y la IA de [[core.ai.py]].
3. **El servidor**: [[server.py]] registra todos los blueprints (ver [[Índice de la API]]).
4. **La verdad del grafo**: el catálogo [[nodes.merge_graph.js]] → snapshot [[data.grafo_v0.json]] → ontología en Postgres ([[ontology.service.py]]).
5. **El dinero**: toda orden pasa por [[brokerage.service.py]] (preview → confirmación humana).

## Capas

| Capa | Archivos | Líneas | De qué trata |
|---|---|---|---|
| [[Capa Interfaz (Khipus OS)]] | 32 | 30.550 | Lo que ves en pantalla: la Cabina / Khipus OS, ventanas, pestañas, mapa, avisos y estilos. |
| [[Capa Chat y agentes]] | 16 | 11.530 | El cerebro conversacional de Khipu, los agentes con su rol, el portero Jev y el lenguaje de comandos. |
| [[Capa Investigación]] | 21 | 5.395 | El enjambre de agentes que investiga: conclusiones (claims) con evidencia citada, cola de trabajos, salud. |
| [[Capa Comité]] | 8 | 6.895 | El comité de inversión: puestos, debate, convicción, tamaño, track record y comité de cartera. |
| [[Capa Ontología y grafo temporal]] | 37 | 19.097 | La fuente de verdad del grafo: eventos bitemporales en Postgres, acciones auditadas, reconciliación y el tiempo en el mapa. |
| [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 24 | 10.533 | Matemática del sistema: matrices y propagación de shocks, tensores, VaR, griegas, escenarios y simulaciones. |
| [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 27 | 14.968 | Todo lo que llega de afuera en vivo: precios, fundamentales, World Monitor, Space Monitor, noticias y el Dossier. |
| [[Capa Dinero (carteras, trading, corretaje)]] | 16 | 10.955 | Carteras, órdenes y corretaje multi-cliente con Alpaca. Regla de oro: toda orden pasa por preview → confirmación humana. |
| [[Capa MCP y API]] | 11 | 6.359 | El servidor MCP para IAs externas (herramientas, tokens kmcp_, OAuth) y la pantalla para conectarlas. |
| [[Capa Voz]] | 4 | 5.090 | Khipu por voz: ElevenLabs (servidor y navegador) y el orbe. |
| [[Capa Infraestructura]] | 48 | 27.525 | La base: server.py, IA en cascada y su gasto, PIN, HTTP saneado, reloj del servidor, service worker, sincronización. |
| [[Capa Datos del catálogo]] | 38 | 68.734 | El catálogo curado de empresas y vínculos (nodes/\*.js), el snapshot data/grafo_v0.json y sus generadores. |
| [[Capa Pruebas]] | 266 | 71.067 | Las pruebas automáticas (pytest) que vigilan cada parte. |
| [[Capa Documentación]] | 32 | 14.818 | Documentos del proyecto (CLAUDE.md, docs/\*.md) y las sesiones de trabajo de docs/ESTADO.md. |
| [[Capa Otros]] | 2 | 703 | Archivos que la tabla de capas todavía no clasifica (se reportan para asignarles capa). |

## Índices

- [[Índice de la API]] — rutas por grupo y quién las llama
- [[API herramientas MCP]] — lo que pueden usar las IAs externas
- [[Índice de variables de entorno]] — solo nombres
- [[Índice de sesiones]] — la historia del proyecto (docs/ESTADO.md)
- [[Índice de pruebas]]
- [[Doc CLAUDE]] — las reglas del proyecto

## Mapa interactivo

Abre `_grafo/mapa.html` en el navegador (doble clic en el archivo dentro de la carpeta `vault`). Los datos en bruto están en `_grafo/graph.json`.
