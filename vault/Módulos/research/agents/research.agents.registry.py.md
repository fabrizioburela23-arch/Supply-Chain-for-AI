---
tipo: "modulo"
capa: "Investigación"
ruta: "research/agents/registry.py"
lenguaje: "python"
lineas: 77
aliases: ["research/agents/registry.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/agents/registry.py

> Módulo · capa [[Capa Investigación]] · 77 líneas · `research/agents/registry.py`

## Para qué sirve

los 8 agentes de Phase 2.

## API pública

- `get_agent(agent_type)` _(línea 76)_

## Depende de

- [[research.agents.base.py]] — importa `Agent`
- [[research.context.py]] — importa `AGENT_NEEDS`

## Lo usan

- [[research.agents.__init__.py]] — lo importa

_Además lo importan 3 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_agents_registry.py]]
- [[tests.test_cleanup_server.py]]
- [[tests.test_committee_os_narr.py]]
