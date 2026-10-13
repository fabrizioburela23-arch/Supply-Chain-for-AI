---
tipo: "modulo"
capa: "MCP y API"
ruta: "mcp_server/contract.py"
lenguaje: "python"
lineas: 296
aliases: ["mcp_server/contract.py"]
tags: ["capa/mcp-api", "tipo/modulo"]
---

# mcp_server/contract.py

> Módulo · capa [[Capa MCP y API]] · 296 líneas · `mcp_server/contract.py`

## Para qué sirve

EL contrato común de las respuestas MCP (ARQUITECTURA_V2 §15; BRECHAS L4-08).

## API pública

- `fit(payload, max_chars, tail_paths=…)` — Recorta `payload` (copia) hasta que su JSON compacto (más la lista `truncation`) entre en max_chars: 1. la lista más pesada se corta un 25 … _(línea 193)_
- `apply(name, res, detail=…, max_chars=…, question=…)` — Resultado crudo de una herramienta → resultado con el contrato (nunca lanza; ante un fallo, el crudo). _(línea 250)_
- `split_common(args)` — Saca detail/max_chars de los argumentos (para el handler) → (args_sin_comunes, detail, max_chars). _(línea 291)_

**Internas** (empiezan con `_`): `_now_iso`, `_dump`, `_finite`, `_nb`, `_sum_company`, `_supply_chain`, `_largest_list`, `_longest_str`, `_size`, `_cut_list`, `_norm_detail`

## Depende de

- [[core.context_engine.py]] — importa `pack_supply_chain`

## Lo usan

- [[mcp_server.tools.py]] — lo importa
- herramienta MCP `cancel_order` → [[API herramientas MCP]]
- herramienta MCP `get_account` → [[API herramientas MCP]]
- herramienta MCP `get_claim_evidence` → [[API herramientas MCP]]
- herramienta MCP `get_committee_memo` → [[API herramientas MCP]]
- herramienta MCP `get_company` → [[API herramientas MCP]]
- herramienta MCP `get_conclusions_board` → [[API herramientas MCP]]
- herramienta MCP `get_ontology_object` → [[API herramientas MCP]]
- herramienta MCP `get_option_greeks` → [[API herramientas MCP]]
- herramienta MCP `get_order_status` → [[API herramientas MCP]]
- herramienta MCP `get_positions` → [[API herramientas MCP]]
- herramienta MCP `get_research` → [[API herramientas MCP]]
- herramienta MCP `get_research_health` → [[API herramientas MCP]]
- herramienta MCP `get_research_job` → [[API herramientas MCP]]
- herramienta MCP `get_risk_report` → [[API herramientas MCP]]
- herramienta MCP `get_supply_chain` → [[API herramientas MCP]]
- herramienta MCP `get_track_record` → [[API herramientas MCP]]
- herramienta MCP `get_world_events` → [[API herramientas MCP]]
- herramienta MCP `list_orders` → [[API herramientas MCP]]
- herramienta MCP `preview_order` → [[API herramientas MCP]]
- herramienta MCP `run_committee` → [[API herramientas MCP]]
- herramienta MCP `run_research` → [[API herramientas MCP]]
- herramienta MCP `search_companies` → [[API herramientas MCP]]
- herramienta MCP `submit_order` → [[API herramientas MCP]]

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_mcp_contract.py]]
