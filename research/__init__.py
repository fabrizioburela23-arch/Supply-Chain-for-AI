"""research/ — PHASE 2 · AGENT RESEARCH SWARM.

Convierte el Live Investment Graph (Phase 1) en un sistema que INVESTIGA:
agentes especializados que leen el grafo + datos en vivo y escriben
CONCLUSIONES DERIVADAS (claims) con evidencia a favor y en contra, horizonte
temporal y confianza calculada — nunca hechos, nunca órdenes de compra/venta.

Tres capas estrictamente separadas (ver docs/CLAIM_MODEL.md):
  RAW DATA      → proveedores (core/providers, core/company_data) — no se toca
  GRAPH FACTS   → ontology/ (events/objects/links) — los agentes NO escriben aquí
  DERIVED CLAIMS→ research_* (este paquete) — lo único que un agente puede crear

Módulos:
  models.py        tablas research_claims / research_evidence / claim_relations /
                   agent_runs / research_jobs (mismo Base que la ontología)
  schemas.py       contratos Pydantic de la salida de un agente (validación)
  llm.py           LLMProvider (generate / structured_generate) + routing por agente
  context.py       ContextBuilder: subgrafo + datos + evidencia numerada (E1..En)
  confidence.py    metodología de confianza con componentes guardados
  contradictions.py detección inicial POTENTIALLY_CONTRADICTS
  agents/          interfaz Agent + agentes especializados
  runner.py        ResearchJob: contexto → agente → validación → persistencia
  router.py        evento → agentes relevantes (Phase 2 event-driven)
  api.py           blueprint /api/research/*
"""
