---
tipo: "capa"
capa: "Cuantitativo (matrices, tensores, riesgo)"
archivos: 24
tags: ["capa/cuantitativo", "tipo/capa"]
---

# Capa Cuantitativo (matrices, tensores, riesgo)

> Matemática del sistema: matrices y propagación de shocks, tensores, VaR, griegas, escenarios y simulaciones.

**24 archivos · 10.409 líneas.** Volver al [[00 Mapa de Khipus]].

## Archivos

- [[matrix.api.py]] — 1.275 líneas · blueprint Flask del motor de matrices: /api/matrix/\*.
- [[matrix.engine.py]] — 1.103 líneas · construcción, modulación y propagación de matrices.
- [[engine.riskreport.js]] — 1.033 líneas · REPORTE DE RIESGO DE CARTERA: VaR + Vega (Kappa).
- [[matrix.tensor.py]] — 846 líneas · ONTOLOGÍA NIVEL 2: el grafo como TENSORES, con números útiles para invertir.
- [[core.risk_report.py]] — 753 líneas · REPORTE DE RIESGO DE CARTERA (VaR, estilo curso MIT).
- [[core.sim_agents.py]] — 706 líneas · Motor de simulación POR AGENTES (interno).
- [[core.scenario_engine.py]] — 548 líneas · ANÁLISIS ESTRUCTURAL de un escenario (sin IA).
- [[engine.hotclient.js]] — 484 líneas · EL cliente de las vistas rápidas del servidor (window.KhipuHot) INFRA_OPERATIVA §4.6-§4.7 (paso 13, 2026-10-13): en el navegador NO queda ningún …
- [[engine.livesim.js]] — 445 líneas · SIMULACIÓN EN VIVO v3 (abierta, no cerrada) Constructor de escenarios: eliges el TIPO de golpe (corte↓, demanda↑, precio, sanción) y el OBJETIVO …
- [[scripts.calibrate_kernel.py]] — 355 líneas · calibra κ (escenario → dinero) con episodios reales (BRECHAS L2-13 / PROP-16; batch I3).
- [[engine.insights.js]] — 344 líneas · INSIGHTS AUTOMÁTICOS (Etapa 5, piel NEXUS) Genera tarjetas de lectura desde la topología + el motor de matrices: - chokepoints (quién arrastra a más …
- [[scripts.bench_scale.py]] — 297 líneas · banco de ESCALA de las vistas rápidas (EXPANSION_5K E0.1; port de exp5k/bench_hot.py).
- [[core.risk_models.py]] — 292 líneas · estimadores ROBUSTOS de riesgo (BRECHAS L2-14/L2-15/L2-16/L2-18; ARQUITECTURA_V2 §9.2-§9.3).
- [[core.options.py]] — 290 líneas · griegas de opciones y REPORTE VEGA (a.k.a. Kappa).
- [[core.scenario_pnl.py]] — 275 líneas · ESCENARIO → DINERO (BRECHAS L2-13 / PROP-16; batch I3, 2026-10-13).
- [[sim.scenario_builder.js]] — 262 líneas · Constructor de seeds para las simulaciones (Khipu Finance) Genera el "seed" textual que alimenta a los motores de simulación con contexto realista: …
- [[engine.matrixview.js]] — 207 líneas · LAS 9 MATRICES dentro de la app (pestaña Análisis) Calcula en el navegador las 9 matrices de relación desde window.LINKS y las dibuja: …
- [[core.screener.py]] — 199 líneas · Screener de crecimiento explosivo: /api/screener/\*.
- [[scripts.gen_synth_graph.py]] — 174 líneas · grafo SINTÉTICO de N empresas para pruebas de escala (EXPANSION_5K E0.1).
- [[engine.compare.js]] — 168 líneas · COMPARAR DOS EMPRESAS lado a lado (decidir entre 2) Overlay NEXUS: elige dos empresas y ve enfrentadas su NRS (término a término), sector, país, …
- [[engine.app_preflight.js]] — 142 líneas · Preflight debounce wiring
- [[matrix.tensor_api.py]] — 115 líneas · /api/tensor/\*: la ontología nivel 2 (matrix/tensor.py) por HTTP.
- [[engine.statematrix.js]] — 76 líneas · ESTADO VISUAL de la simulación (solo animación; SIN matemática de contagio) Paso 13 de INFRA_OPERATIVA (2026-10-13): el navegador ya NO propaga …
- [[matrix.__init__.py]] — 20 líneas · el motor de matrices de Khipus (Etapa 3, 2026-07).

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| usa a | [[Capa Infraestructura]] | 35 |
| la usa | [[Capa Interfaz (Khipus OS)]] | 18 |
| la usa | [[Capa Infraestructura]] | 15 |
| usa a | [[Capa Interfaz (Khipus OS)]] | 14 |
| usa a | [[Capa Ontología y grafo temporal]] | 12 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 12 |
| usa a | [[Capa Datos del catálogo]] | 10 |
| la usa | [[Capa Chat y agentes]] | 9 |
| la usa | [[Capa MCP y API]] | 8 |
| la usa | [[Capa Dinero (carteras, trading, corretaje)]] | 4 |
| la usa | [[Capa Ontología y grafo temporal]] | 4 |
| la usa | [[Capa Comité]] | 3 |
| la usa | [[Capa Voz]] | 3 |
| la usa | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 2 |
| usa a | [[Capa MCP y API]] | 2 |
| usa a | [[Capa Chat y agentes]] | 1 |
| usa a | [[Capa Dinero (carteras, trading, corretaje)]] | 1 |
