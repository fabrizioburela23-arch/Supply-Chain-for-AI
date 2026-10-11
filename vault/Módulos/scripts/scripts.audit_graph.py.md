---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "scripts/audit_graph.py"
lenguaje: "python"
lineas: 614
aliases: ["scripts/audit_graph.py"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# scripts/audit_graph.py

> Módulo · capa [[Capa Ontología y grafo temporal]] · 614 líneas · `scripts/audit_graph.py`

## Para qué sirve

Auditoría automática del grafo (misión de reparación, G1).

## API pública

- `load_snapshot(path=…)` _(línea 127)_
- `load_vocab(path=…)` — {'rel_types': set, 'structural': list(ordenada), 'symmetric': set}. _(línea 132)_
- `load_baseline(path=…)` _(línea 150)_
- `norm_label(label)` — minúsculas, sin paréntesis finales, sin sufijos corporativos (Inc/Corp/ Ltd/Co/Company/Group/Trust/Holdings/PLC), sin … _(línea 160)_
- `audit_snapshot(snap, vocab=…)` _(línea 214)_
- `summary(res, lang=…)` _(línea 374)_
- `compare_baseline(res, baseline)` — {'worse': {cat: (antes, ahora)}, 'better': {...}, 'ok': bool}. Solo RATCHET. _(línea 392)_
- `build_baseline(res)` _(línea 408)_
- `audit_db(snap, vocab=…, sample=…)` — Compara los links vigentes de la base (links.valid_to IS NULL) con el snapshot. Nunca escribe: la transacción se abre READ ONLY. _(línea 424)_
- `to_markdown(res, baseline=…, cmp=…, limit=…, db=…)` _(línea 509)_
- `main(argv=…)` _(línea 566)_

**Internas** (empiezan con `_`): `_resolver`, `_name_variants`, `_name_pattern`, `_fmt_finding`

## Depende de

- [[ontology.db.py]] — importa `session_scope`
- [[data.grafo_v0.json]] — lo nombra por su ruta
- [[data.graph_audit_baseline.json]] — lo nombra por su ruta
- [[ontology.vocabulary.json]] — lo nombra por su ruta

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

_Además lo importan 1 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV DATABASE_URL]]

## Pruebas que lo cubren

- [[tests.test_graph_audit.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (ff) — ONTOLOGÍA NIVEL 2 - TENSORES + AUTO-CONEXIÓN (sw v241)]]
- [[Sesión 2026-10-04 (i) — MISIÓN DE REPARACIÓN P1 GRAFO + P2 WORLD MONITOR Y OPERACIÓN]]
