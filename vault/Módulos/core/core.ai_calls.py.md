---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/ai_calls.py"
lenguaje: "python"
lineas: 317
aliases: ["core/ai_calls.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/ai_calls.py

> Módulo · capa [[Capa Infraestructura]] · 317 líneas · `core/ai_calls.py`

## Para qué sirve

registro append-only de CADA pedido a la IA (docs/INFRA_OPERATIVA.md §2.6, paso 21; GV-11).

## API pública

- `sha_text(s)` _(línea 57)_
- `attribute(decision_id, collect=…, durability=…)` — Las llamadas de IA de este bloque (y de los hilos que lo hereden vía core/ai_usage.bind) llevan este `decision_id`; si `collect` es una … _(línea 63)_
- `snapshot()` — Lo que un hilo del pool debe heredar (core/ai_usage.bind). Nunca lanza. _(línea 74)_
- `restore(snap)` _(línea 83)_
- `begin(system, prompt, tier=…, max_tokens=…, want_json=…, model=…)` — Arma la fila (en memoria) ANTES de llamar al proveedor. Barato: los sha y los blobs se calculan en el hilo escritor. _(línea 114)_
- `finish(rec, text=…, used=…, acc=…, ok=…, error=…, tried=…)` — Completa la fila con lo que pasó (texto, modelo real, tokens/costo medidos por core/ai_usage.meter). _(línea 136)_
- `held()` — El guardián de cifras (core/ai._ai_complete) retiene las filas de su bloque para anotarles su veredicto antes de encolarlas. Devuelve la … _(línea 159)_
- `submit(rec)` — Encola la fila (o la retiene si el guardián está mirando). Nunca lanza; nunca bloquea. _(línea 172)_
- `flush(max_rows=…)` — Escribe lo encolado (una transacción por lote). → filas escritas. Lo usan el hilo escritor y las pruebas. _(línea 237)_
- `stats()` _(línea 307)_

**Internas** (empiezan con `_`): `_db_on`, `_scope_decision`, `_decision_now`, `_blob`, `_rows`, `_flush`, `_ensure_writer`, `_reset_for_tests`

## Depende de

- [[core.ai_usage.py]] — importa `ai_usage`
- [[core.decisions.py]] — importa `canonical`, `decisions`
- [[core.identity.py]] — importa `hash_id`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[ontology.ledger_models.py]] — importa `AICall`, `DecisionBlob`

## Lo usan

- [[core.ai.py]] — lo importa
- [[core.ai_usage.py]] — lo importa
- [[core.decision_sites.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa
- [[core.ledger_api.py]] — lo importa
- [[matrix.api.py]] — lo importa

_Además lo importan 6 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.conftest.py]]
- [[tests.test_ai_calls.py]]
- [[tests.test_khipus_os_perf.py]]
- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_ledger_review_fixes.py]]
- [[tests.test_review_batch_g.py]]
