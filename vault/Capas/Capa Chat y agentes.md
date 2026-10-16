---
tipo: "capa"
capa: "Chat y agentes"
archivos: 16
tags: ["capa/chat-agentes", "tipo/capa"]
---

# Capa Chat y agentes

> El cerebro conversacional de Khipu, los agentes con su rol, el portero Jev y el lenguaje de comandos.

**16 archivos · 11.439 líneas.** Volver al [[00 Mapa de Khipus]].

## Archivos

- [[core.khipu_chat.py]] — 3.759 líneas · EL cerebro conversacional de Khipu (texto).
- [[engine.localcharts.js]] — 1.696 líneas · CANVAS: ROUTER DE INTENCIÓN + GRÁFICOS SIN IA (Etapa G 2026-07-11 · Etapa I 2026-07-12 · ROUTER 2026-10-02)
- [[engine.khipu_chat.js]] — 1.450 líneas · EL CHAT de Khipu (texto), compartido por la Cabina (engine/cockpit.js) y el Command Center (engine/command_center.js).
- [[engine.app_canvas.js]] — 688 líneas · palette & helpers
- [[core.agents_api.py]] — 448 líneas · PERFILES DE LOS AGENTES de Khipus OS (2026-10-06).
- [[engine.command_center.js]] — 433 líneas · Khipu Command Center (Khipu Finance) UN SOLO Khipu: el botón original del header lo abre. NO hay orbe flotante. El panel (input + feed de resultados) …
- [[engine.pickers.js]] — 431 líneas · opciones FIJAS en vez de texto libre (pedido de Fabrizio 2026-10-05: "donde se escriban cosas fijas como tickers de empresas no quiero que te deje …
- [[engine.resolve.js]] — 417 líneas · RESOLUTOR DE EMPRESAS + SUPERFICIE DE RESULTADOS (2026-07) Feedback real de Fabrizio: "bixby a veces me dice que una empresa no existe o no me …
- [[core.decide.py]] — 415 líneas · JEV (TypeSafe AI, modelo "System One"): DECISIONES, no texto.
- [[research.agent_skills.py]] — 410 líneas · HABILIDADES PROPIAS de cada agente (2026-10-06).
- [[engine.khipu_lang.js]] — 381 líneas · Fase 4 del roadmap de ontología: lenguaje de comandos KHIPU, corto y componible: &lt;ENTIDAD> &lt;FUNCIÓN> [ARGS]. Se intenta ANTES de mandar el …
- [[core.canvas_spec.py]] — 366 líneas · Canvas IA: criterio de tipo de gráfico + validación.
- [[research.ask_agent.py]] — 301 líneas · PREGUNTARLE A UN ANALISTA dentro de la conversación.
- [[core.semantic.py]] — 144 líneas · CAPA 2 (PRECONSCIENTE): el grafo semántico activo.
- [[engine.canvas-data.js]] — 72 líneas · Enriquecimiento de Canvas IA con datos en vivo (Khipu) Detecta empresas/tickers mencionados en una consulta y trae precios REALES de Finnhub (vía …
- [[core.decide_api.py]] — 28 líneas · /api/decide/\*: estado del modo sombra de Jev (lectura, PIN de operador).

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| usa a | [[Capa Infraestructura]] | 31 |
| usa a | [[Capa Interfaz (Khipus OS)]] | 28 |
| la usa | [[Capa Interfaz (Khipus OS)]] | 25 |
| usa a | [[Capa Datos del catálogo]] | 10 |
| usa a | [[Capa Comité]] | 10 |
| usa a | [[Capa Ontología y grafo temporal]] | 10 |
| usa a | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 9 |
| usa a | [[Capa Investigación]] | 9 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 9 |
| la usa | [[Capa Infraestructura]] | 7 |
| la usa | [[Capa Comité]] | 6 |
| la usa | [[Capa Dinero (carteras, trading, corretaje)]] | 5 |
| la usa | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 5 |
| usa a | [[Capa Dinero (carteras, trading, corretaje)]] | 4 |
| usa a | [[Capa MCP y API]] | 4 |
| la usa | [[Capa Voz]] | 2 |
| la usa | [[Capa Cuantitativo (matrices, tensores, riesgo)]] | 1 |
| la usa | [[Capa MCP y API]] | 1 |
| usa a | [[Capa Voz]] | 1 |
