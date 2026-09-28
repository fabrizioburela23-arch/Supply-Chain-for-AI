"""research/agents — interfaz común + registro de agentes especializados.

Cada agente es una instancia de Agent con SU especificación (qué lee, qué
herramientas puede usar, a qué eventos responde, su enfoque y su ruta de
modelos). Lo que TODOS pueden escribir es lo mismo y está cerrado:
claims, evidence, counter_evidence y anotaciones en research_* — nunca hechos
del grafo, datos de mercado, documentos fuente ni identidades canónicas
(ver WRITE_PERMISSIONS y docs/AGENT_SECURITY.md).
"""
from research.agents.base import Agent, WRITE_PERMISSIONS  # noqa: F401
from research.agents.registry import AGENTS, AGENTS_BY_TYPE, get_agent  # noqa: F401
