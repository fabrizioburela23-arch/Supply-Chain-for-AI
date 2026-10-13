---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/governance_preview.py"
lenguaje: "python"
lineas: 182
aliases: ["core/governance_preview.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/governance_preview.py

> Módulo · capa [[Capa Infraestructura]] · 182 líneas · `core/governance_preview.py`

## Para qué sirve

"¿qué cambia para mí?" de una versión de artefacto ANTES de activarla (paso 12; pieza mínima del flujo de gobernanza §5.3 de docs/INFRA_OPERATIVA.md).

## API pública

- `preview(selection)` — {selection, release_hash, generation, params_diff, kernel?, nrs_affected, summary_es/en, compute_ms}. _(línea 127)_
- `reset()` _(línea 180)_

**Internas** (empiezan con `_`): `_build`, `_params_diff`, `_victims`, `_kernel_compare`, `_summary`

## Depende de

- [[core.__init__.py]] — importa `graph_core`, `hot`, `impact`, `source`
- [[core.governance.py]] — importa `governance`
- [[matrix.engine.py]] — importa `engine`

## Lo usan

- [[core.governance_api.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_governance_activation.py]]
