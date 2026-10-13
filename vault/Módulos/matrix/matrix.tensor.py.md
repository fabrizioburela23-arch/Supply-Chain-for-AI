---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "matrix/tensor.py"
lenguaje: "python"
lineas: 528
aliases: ["matrix/tensor.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# matrix/tensor.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 528 líneas · `matrix/tensor.py`

## Para qué sirve

ONTOLOGÍA NIVEL 2: el grafo como TENSORES, con números útiles para invertir.

## API pública

- clase `Model` — Tensores del grafo ya calculados (inmutable; se reemplaza entero al cambiar la entrada). _(línea 195)_
- `model(force=…, snap=…, view=…)` — Modelo vigente (caché). Se reconstruye si cambia la GENERACIÓN del grafo (paso 8: antes, la fecha del archivo del snapshot) o la versión de … _(línea 306)_
- `graph_version()` — La generación del grafo del modelo vigente (tests/test_ops_single_source.py). _(línea 326)_
- `structure(nid, m=…, top=…)` — Ficha estructural de una empresa (contrato estable; solo se agregan campos). _(línea 342)_
- `peers(nid, m=…, n=…)` — Comparables: mismos proveedores/clientes (coseno del perfil) + rasgos (X) + misma categoría. _(línea 393)_
- `ranking(m=…, by=…, limit=…)` _(línea 409)_
- `suggest_links(nid=…, new=…, m=…, n=…, exclude_existing=…)` — Proveedores y clientes PROBABLES de una empresa (existente o nueva). Solo propuestas. _(línea 445)_
- `evaluate(frac=…, seed=…, k=…, snap=…, max_cases=…)` — Calidad REAL de la auto-conexión: se ocultan vínculos de flujo reales y se mide si vuelven a aparecer entre las k primeras propuestas … _(línea 492)_
- `status()` _(línea 522)_

**Internas** (empiezan con `_`): `_load_snapshot`, `_psi_from_impact`, `_core_for`, `_impact_for`, `_FlowImpact`, `_flow_impact`, `_caps_live`, `_caps_private`, `_country`, `_norm_txt`, `_tokens`, `_conc_label`, `_peer_weights`

## Depende de

- [[core.__init__.py]] — importa `graph_core`, `hot`, `impact`, `source`
- [[core.entities.py]] — importa `resolve`
- [[core.governance.py]] — importa `governance`
- [[core.live_caps.py]] — importa `live_caps`
- [[core.world.py]] — importa `country_key`
- [[matrix.engine.py]] — importa `engine`
- [[mcp_server.tools.py]] — importa `_private_valuations`
- [[ontology.vocabulary.py]] — importa `vocabulary`

## Lo usan

- [[matrix.tensor_api.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[ontology.actions.py]] — lo importa
- [[research.agent_skills.py]] — lo importa
- herramienta MCP `find_similar_entities` → [[API herramientas MCP]]
- herramienta MCP `get_company` → [[API herramientas MCP]]
- herramienta MCP `get_exposure` → [[API herramientas MCP]]

_Además lo importan 9 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_cleanup_server.py]]
- [[tests.test_governance.py]]
- [[tests.test_governance_seed_parity.py]]
- [[tests.test_hot_views_parity.py]]
- [[tests.test_kernel_reference_figures.py]]
- [[tests.test_mcp.py]]
- [[tests.test_ops_single_source.py]]
- [[tests.test_tensor.py]]
- [[tests.test_tensor_autolink.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (ff) — ONTOLOGÍA NIVEL 2 - TENSORES + AUTO-CONEXIÓN (sw v241)]]
