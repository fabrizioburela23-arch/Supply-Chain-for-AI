---
tipo: "inicio"
tags: ["tipo/inicio"]
---

# 00 Mapa de Khipus

Bienvenido. Esta bóveda es un **mapa vivo del código de Khipus Finance AI**: cada archivo, ruta de la API, variable de entorno y sesión de trabajo es una nota, y los enlaces entre notas son las conexiones reales del código. La genera `scripts/build_vault.py` sin IA, leyendo el repositorio.

**190 archivos de código (114.802 líneas) · 239 rutas HTTP · 23 herramientas MCP · 160 variables de entorno · 96 sesiones de trabajo.**

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
| [[Capa Interfaz (Khipus OS)]] | 16 | 25.225 | Lo que ves en pantalla: la Cabina / Khipus OS, ventanas, pestañas, mapa, avisos y estilos. |
| [[Capa Chat y agentes]] | 15 | 9.525 | El cerebro conversacional de Khipu, los agentes con su rol, el portero Jev y el lenguaje de comandos. |
| [[Capa Investigación]] | 21 | 5.038 | El enjambre de agentes que investiga: conclusiones (claims) con evidencia citada, cola de trabajos, salud. |
| [[Capa Comité]] | 8 | 6.581 | El comité de inversión: puestos, debate, convicción, tamaño, track record y comité de cartera. |
| [[Capa Ontología y grafo temporal]] | 26 | 11.218 | La fuente de verdad del grafo: eventos bitemporales en Postgres, acciones auditadas, reconciliación y el tiempo en el mapa. |
| [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 18 | 7.143 | Matemática del sistema: matrices y propagación de shocks, tensores, VaR, griegas, escenarios y simulaciones. |
| [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 27 | 14.556 | Todo lo que llega de afuera en vivo: precios, fundamentales, World Monitor, Space Monitor, noticias y el Dossier. |
| [[Capa Dinero (carteras, trading, corretaje)]] | 13 | 7.814 | Carteras, órdenes y corretaje multi-cliente con Alpaca. Regla de oro: toda orden pasa por preview → confirmación humana. |
| [[Capa MCP y API]] | 9 | 4.569 | El servidor MCP para IAs externas (herramientas, tokens kmcp_, OAuth) y la pantalla para conectarlas. |
| [[Capa Voz]] | 3 | 4.470 | Khipu por voz: ElevenLabs (servidor y navegador) y el orbe. |
| [[Capa Infraestructura]] | 29 | 17.731 | La base: server.py, IA en cascada y su gasto, PIN, HTTP saneado, reloj del servidor, service worker, sincronización. |
| [[Capa Datos del catálogo]] | 33 | 64.240 | El catálogo curado de empresas y vínculos (nodes/\*.js), el snapshot data/grafo_v0.json y sus generadores. |
| [[Capa Pruebas]] | 151 | 44.470 | Las pruebas automáticas (pytest) que vigilan cada parte. |
| [[Capa Documentación]] | 26 | 11.265 | Documentos del proyecto (CLAUDE.md, docs/\*.md) y las sesiones de trabajo de docs/ESTADO.md. |

## Índices

- [[Índice de la API]] — rutas por grupo y quién las llama
- [[API herramientas MCP]] — lo que pueden usar las IAs externas
- [[Índice de variables de entorno]] — solo nombres
- [[Índice de sesiones]] — la historia del proyecto (docs/ESTADO.md)
- [[Índice de pruebas]]
- [[Doc CLAUDE]] — las reglas del proyecto

## Mapa interactivo

Abre `_grafo/mapa.html` en el navegador (doble clic en el archivo dentro de la carpeta `vault`). Los datos en bruto están en `_grafo/graph.json`.
