---
tipo: "capa"
capa: "Investigación"
archivos: 21
tags: ["capa/investigacion", "tipo/capa"]
---

# Capa Investigación

> El enjambre de agentes que investiga: conclusiones (claims) con evidencia citada, cola de trabajos, salud.

**21 archivos · 5.023 líneas.** Volver al [[00 Mapa de Khipus]].

## Archivos

- [[research.runner.py]] — 994 líneas · ejecución de un ResearchJob (vertical slice → general).
- [[engine.research.js]] — 591 líneas · PHASE 2 · INVESTIGACIÓN IA (Agent Research Swarm)
- [[research.context.py]] — 572 líneas · ContextBuilder: NO se manda el grafo entero al LLM.
- [[research.models.py]] — 401 líneas · tablas de la capa DERIVED CLAIMS (Phase 2).
- [[research.api.py]] — 324 líneas · blueprint /api/research/\* (Phase 2).
- [[research.llm.py]] — 301 líneas · abstracción de proveedor de modelos (no acoplada a nadie).
- [[research.analytics.py]] — 269 líneas · ANÁLISIS CUANTITATIVO determinista para los agentes.
- [[research.health.py]] — 202 líneas · "¿puedo investigar ahora?" en UNA foto (R6, misión de reparación).
- [[research.falsifiers.py]] — 184 líneas · falsadores ESTRUCTURADOS y verificables (C8, misión de reparación 2026-10-04).
- [[core.sec.py]] — 143 líneas · SEC EDGAR como EVIDENCIA PRIMARIA (Phase 2).
- [[research.contradictions.py]] — 143 líneas · detección INICIAL de tensiones entre claims.
- [[research.agents.base.py]] — 141 líneas · la interfaz Agent.
- [[research.confidence.py]] — 137 líneas · confianza de una claim (metodología conf-v2).
- [[research.schemas.py]] — 134 líneas · contrato de la salida de un agente (Pydantic v2).
- [[research.router.py]] — 133 líneas · evento → relevancia → agentes (Phase 2 event-driven).
- [[research.auto_events.py]] — 129 líneas · eventos AUTOMÁTICOS del mercado real (Phase 2).
- [[research.agents.registry.py]] — 77 líneas · los 8 agentes de Phase 2.
- [[research.errors.py]] — 75 líneas · traduce errores técnicos de la IA a lenguaje simple.
- [[core.websearch.py]] — 37 líneas · búsqueda web real para investigación autónoma.
- [[research.__init__.py]] — 25 líneas · PHASE 2 · AGENT RESEARCH SWARM.
- [[research.agents.__init__.py]] — 11 líneas · interfaz común + registro de agentes especializados.

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| usa a | [[Capa Infraestructura]] | 20 |
| la usa | [[Capa Comité]] | 15 |
| usa a | [[Capa Ontología y grafo temporal]] | 15 |
| la usa | [[Capa Chat y agentes]] | 9 |
| la usa | [[Capa Infraestructura]] | 6 |
| la usa | [[Capa Interfaz (Khipus OS)]] | 4 |
| la usa | [[Capa Ontología y grafo temporal]] | 4 |
| usa a | [[Capa Interfaz (Khipus OS)]] | 4 |
| la usa | [[Capa MCP y API]] | 3 |
| usa a | [[Capa Comité]] | 3 |
| usa a | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 3 |
| la usa | [[Capa Dinero (carteras, trading, corretaje)]] | 2 |
| la usa | [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] | 1 |
| la usa | [[Capa Voz]] | 1 |
