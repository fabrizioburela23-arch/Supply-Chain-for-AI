---
tipo: "capa"
capa: "Cuantitativo (matrices, tensores, riesgo)"
archivos: 17
tags: ["capa/cuantitativo", "tipo/capa"]
---

# Capa Cuantitativo (matrices, tensores, riesgo)

> Matemática del sistema: matrices y propagación de shocks, tensores, VaR, griegas, escenarios y simulaciones.

**17 archivos · 6.987 líneas.** Volver al [[00 Mapa de Khipus]].

## Archivos

- [[matrix.api.py]] — 1.064 líneas · blueprint Flask del motor de matrices: /api/matrix/\*.
- [[engine.riskreport.js]] — 992 líneas · REPORTE DE RIESGO DE CARTERA: VaR + Vega (Kappa).
- [[matrix.engine.py]] — 759 líneas · construcción, modulación y propagación de matrices.
- [[core.sim_agents.py]] — 646 líneas · Motor de simulación POR AGENTES (interno).
- [[matrix.tensor.py]] — 523 líneas · ONTOLOGÍA NIVEL 2: el grafo como TENSORES, con números útiles para invertir.
- [[engine.livesim.js]] — 435 líneas · SIMULACIÓN EN VIVO v3 (abierta, no cerrada) Constructor de escenarios: eliges el TIPO de golpe (corte↓, demanda↑, precio, sanción) y el OBJETIVO …
- [[core.scenario_engine.py]] — 404 líneas · ANÁLISIS ESTRUCTURAL de un escenario (sin IA).
- [[core.risk_report.py]] — 398 líneas · REPORTE DE RIESGO DE CARTERA (VaR, estilo curso MIT).
- [[engine.insights.js]] — 360 líneas · INSIGHTS AUTOMÁTICOS (Etapa 5, piel NEXUS) Genera tarjetas de lectura desde la topología + el motor de matrices: - chokepoints (quién arrastra a más …
- [[sim.scenario_builder.js]] — 262 líneas · Constructor de seeds para las simulaciones (Khipu Finance) Genera el "seed" textual que alimenta a los motores de simulación con contexto realista: …
- [[engine.statematrix.js]] — 234 líneas · MOTOR DE ESTADOS REACTIVO (client-side, 60 fps) El "sistema nervioso" de Khipus: cada empresa tiene un VECTOR DE ESTADO (signos vitales); las …
- [[core.options.py]] — 214 líneas · griegas de opciones y REPORTE VEGA (a.k.a. Kappa).
- [[engine.matrixview.js]] — 207 líneas · LAS 9 MATRICES dentro de la app (pestaña Análisis) Calcula en el navegador las 9 matrices de relación desde window.LINKS y las dibuja: …
- [[core.screener.py]] — 196 líneas · Screener de crecimiento explosivo: /api/screener/\*.
- [[engine.compare.js]] — 168 líneas · COMPARAR DOS EMPRESAS lado a lado (decidir entre 2) Overlay NEXUS: elige dos empresas y ve enfrentadas su NRS (término a término), sector, país, …
- [[matrix.tensor_api.py]] — 105 líneas · /api/tensor/\*: la ontología nivel 2 (matrix/tensor.py) por HTTP.
- [[matrix.__init__.py]] — 20 líneas · el motor de matrices de Khipus (Etapa 3, 2026-07).

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| la usa | [[Capa Interfaz (Khipus OS)]] | 16 |
| usa a | [[Capa Infraestructura]] | 15 |
| usa a | [[Capa Interfaz (Khipus OS)]] | 11 |
| la usa | [[Capa Chat y agentes]] | 9 |
| usa a | [[Capa Datos del catálogo]] | 8 |
| usa a | [[Capa Ontología y grafo temporal]] | 8 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 8 |
| la usa | [[Capa Infraestructura]] | 7 |
| la usa | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 4 |
| la usa | [[Capa Voz]] | 4 |
| la usa | [[Capa Comité]] | 3 |
| la usa | [[Capa Dinero (carteras, trading, corretaje)]] | 3 |
| la usa | [[Capa MCP y API]] | 3 |
| la usa | [[Capa Ontología y grafo temporal]] | 2 |
| usa a | [[Capa Chat y agentes]] | 1 |
| usa a | [[Capa Dinero (carteras, trading, corretaje)]] | 1 |
| usa a | [[Capa MCP y API]] | 1 |
