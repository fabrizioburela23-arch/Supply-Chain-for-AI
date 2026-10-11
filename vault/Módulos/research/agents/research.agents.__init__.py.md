---
tipo: "modulo"
capa: "Investigación"
ruta: "research/agents/__init__.py"
lenguaje: "python"
lineas: 11
aliases: ["research/agents/__init__.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/agents/__init__.py

> Módulo · capa [[Capa Investigación]] · 11 líneas · `research/agents/__init__.py`

## Para qué sirve

interfaz común + registro de agentes especializados.

## API pública

_Sin funciones ni clases públicas de nivel superior._

## Depende de

- [[research.agents.base.py]] — importa `Agent`, `WRITE_PERMISSIONS`
- [[research.agents.registry.py]] — importa `AGENTS`, `AGENTS_BY_TYPE`, `get_agent`

## Lo usan

- [[research.api.py]] — lo importa
- [[research.router.py]] — lo importa
- [[research.runner.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_research.py]]
