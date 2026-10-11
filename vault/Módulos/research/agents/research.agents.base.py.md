---
tipo: "modulo"
capa: "Investigación"
ruta: "research/agents/base.py"
lenguaje: "python"
lineas: 141
aliases: ["research/agents/base.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/agents/base.py

> Módulo · capa [[Capa Investigación]] · 141 líneas · `research/agents/base.py`

## Para qué sirve

la interfaz Agent.

## API pública

- clase `Agent` _(línea 57)_
- `salvage(obj, valid_refs, evidence)` — Limpia en el lugar un resultado casi válido. Devuelve los errores que persisten (lista vacía = rescatado). Las claims descartadas se anotan … _(línea 116)_

## Depende de

- [[core.numbers.py]] — importa `check_numbers`, `evidence_numbers`, `unsupported_money`
- [[research.context.py]] — importa `render_context`
- [[research.llm.py]] — importa `RoutedProvider`, `route_for`
- [[research.schemas.py]] — importa `AgentResearchResult`, `check_refs`, `json_schema_hint`

## Lo usan

- [[research.agents.__init__.py]] — lo importa
- [[research.agents.registry.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_phase3.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-02 (b) — COMITÉ CON ANÁLISIS REAL DE IA + INVESTIGACIÓN QUE NO SE CAE]]
