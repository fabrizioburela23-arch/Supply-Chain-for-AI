---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "matrix/tensor.py"
lenguaje: "python"
lineas: 459
aliases: ["matrix/tensor.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# matrix/tensor.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 459 líneas · `matrix/tensor.py`

## Para qué sirve

ONTOLOGÍA NIVEL 2: el grafo como TENSORES, con números útiles para invertir.

## API pública

- clase `Model` — Tensores del grafo ya calculados (inmutable; se reemplaza entero al cambiar la entrada). _(línea 131)_
- `model(force=…, snap=…)` — Modelo vigente (caché). Se reconstruye si cambia el snapshot o la versión de las caps en vivo. _(línea 246)_
- `structure(nid, m=…, top=…)` — Ficha estructural de una empresa (contrato estable; solo se agregan campos). _(línea 275)_
- `peers(nid, m=…, n=…)` — Comparables: mismos proveedores/clientes (coseno del perfil) + rasgos (X) + misma categoría. _(línea 325)_
- `ranking(m=…, by=…, limit=…)` _(línea 341)_
- `suggest_links(nid=…, new=…, m=…, n=…, exclude_existing=…)` — Proveedores y clientes PROBABLES de una empresa (existente o nueva). Solo propuestas. _(línea 377)_
- `evaluate(frac=…, seed=…, k=…, snap=…, max_cases=…)` — Calidad REAL de la auto-conexión: se ocultan vínculos de flujo reales y se mide si vuelven a aparecer entre las k primeras propuestas … _(línea 424)_
- `status()` _(línea 454)_

**Internas** (empiezan con `_`): `_load_snapshot`, `_caps_live`, `_caps_private`, `_country`, `_norm_txt`, `_tokens`, `_conc_label`, `_peer_weights`

## Depende de

- [[core.entities.py]] — importa `resolve`
- [[core.live_caps.py]] — importa `live_caps`
- [[core.world.py]] — importa `country_key`
- [[matrix.engine.py]] — importa `engine`
- [[mcp_server.tools.py]] — importa `_private_valuations`
- [[ontology.vocabulary.py]] — importa `vocabulary`
- [[data.grafo_v0.json]] — lo nombra por su ruta

## Lo usan

- [[matrix.tensor_api.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[ontology.actions.py]] — lo importa
- [[research.agent_skills.py]] — lo importa
- herramienta MCP `get_company` → [[API herramientas MCP]]

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_tensor.py]]
- [[tests.test_tensor_autolink.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (ff) — ONTOLOGÍA NIVEL 2 - TENSORES + AUTO-CONEXIÓN (sw v241)]]
