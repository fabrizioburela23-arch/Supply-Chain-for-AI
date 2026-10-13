---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/governance_preview.py"
lenguaje: "python"
lineas: 191
aliases: ["core/governance_preview.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/governance_preview.py

> Módulo · capa [[Capa Infraestructura]] · 191 líneas · `core/governance_preview.py`

## Para qué sirve

"¿qué cambia para mí?" de una versión de artefacto ANTES de activarla (paso 12; pieza mínima del flujo de gobernanza §5.3 de docs/INFRA_OPERATIVA.md).

## API pública

- `preview(selection, focus=…)` — {selection, release_hash, generation, params_diff, kernel?, nrs_affected, summary_es/en, for_me, compute_ms}. `focus` (paso 25): ids de las … _(línea 127)_
- `reset()` _(línea 189)_

**Internas** (empiezan con `_`): `_build`, `_params_diff`, `_victims`, `_kernel_compare`, `_summary`

## Depende de

- [[core.__init__.py]] — importa `graph_core`, `hot`, `impact`, `source`
- [[core.governance.py]] — importa `governance`
- [[core.governance_flow.py]] — importa `governance_flow`
- [[matrix.engine.py]] — importa `engine`

## Lo usan

- [[core.governance_api.py]] — lo importa
- [[core.governance_flow.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_governance_activation.py]]
- [[tests.test_governance_flow.py]]
