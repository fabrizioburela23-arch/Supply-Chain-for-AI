---
tipo: "modulo"
capa: "Investigación"
ruta: "research/schemas.py"
lenguaje: "python"
lineas: 134
aliases: ["research/schemas.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/schemas.py

> Módulo · capa [[Capa Investigación]] · 134 líneas · `research/schemas.py`

## Para qué sirve

contrato de la salida de un agente (Pydantic v2).

## API pública

- clase `ClaimOut` _(línea 26)_
- clase `AgentResearchResult` _(línea 90)_
- `check_refs(result, valid_refs)` — Reglas que dependen del contexto (no expresables en el tipo): cada ref citada debe existir en el paquete; una misma ref no puede ser a la … _(línea 97)_
- `json_schema_hint()` — Esquema compacto para el prompt (lo que el modelo debe devolver). _(línea 115)_

## Depende de

- [[research.falsifiers.py]] — importa `FalsifierRule`, `direction_errors`
- [[research.models.py]] — importa `HORIZONS`, `STANCES`

## Lo usan

- [[research.agents.base.py]] — lo importa

_Además lo importan 4 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_phase3.py]]
- [[tests.test_repair_committee.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_research.py]]
