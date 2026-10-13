---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "ontology/reconcile.py"
lenguaje: "python"
lineas: 790
aliases: ["ontology/reconcile.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# ontology/reconcile.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 790 líneas · `ontology/reconcile.py`

## Para qué sirve

G3 (misión de reparación 2026-10-04): RECONCILIACIÓN append-only entre el catálogo (data/grafo_v0.json, la verdad del MAPA/MCP) y Postgres (la verdad del GRAFO: motor de matrices, NRS servidor, Grafo Temporal, get_ontology_object).

## API pública

- clase `ReconcileError` — Mensaje en español (args[0]) + inglés (`en`) para la UI bilingüe. _(línea 63)_
- `load_snapshot(path=…)` _(línea 75)_
- `snapshot_from_dict(g, path=…)` _(línea 82)_
- `canon(alias_map, oid)` _(línea 100)_
- `build_plan(session, snap)` _(línea 181)_
- `render_markdown(plan, dbname=…, limit_rows=…, lang=…)` _(línea 401)_
- `markdown_to_html(md, title=…)` — Conversor MÍNIMO y seguro (todo se escapa) para el informe: títulos, tablas, listas numeradas, párrafos, \*\*negrita\*\*, \*cursiva\* y `código`. _(línea 469)_
- `new_run_id()` _(línea 521)_
- `apply_plan(session_scope, snap, include=…, confirm_db=…, actor=…, run_id=…, log=…, expect=…)` — Aplica por categoría, RE-CALCULANDO el plan antes de cada una (la fusión de alias cambia qué filas existen). Cada categoría en su propia … _(línea 543)_
- `rollback_run(session, run_id, confirm_db=…, actor=…)` — Deshace una corrida con NUEVOS eventos (canal reconcile_v0_rollback:&lt;run_id>). No borra nada. No se puede deshacer un rollback (sería otra … _(línea 660)_
- `list_runs(session, limit=…)` _(línea 783)_

**Internas** (empiezan con `_`): `_w`, `_same_w`, `_is_genesis`, `_now`, `_load_db`, `_row_scope`, `_creation_order`, `_human_rejections`, `_cell`, `_db_name`, `_check_confirm`, `_busy`, `_apply_locked`, `_current_incarnation`

## Depende de

- [[ontology.actions.py]] — importa `FusionarEntidadInput`, `RetractarVinculoInput`, `fusionar_entidad`, `retractar_vinculo`
- [[ontology.db.py]] — importa `_get_engine`
- [[ontology.models.py]] — importa `Event`, `EventType`, `LinkRecord`, `ObjectRecord`
- [[ontology.service.py]] — importa `_creation_event_for`, `apply_event`
- [[data.grafo_v0.json]] — lo nombra por su ruta

## Lo usan

- [[core.ops_check.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[scripts.build_graph_review.py]] — lo importa
- [[scripts.reconcile_v0_to_ontology.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_ops_single_source.py]]
- [[tests.test_reconcile.py]]
- [[tests.test_repair_ontology_review.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-04 (i) — MISIÓN DE REPARACIÓN P1 GRAFO + P2 WORLD MONITOR Y OPERACIÓN]]
