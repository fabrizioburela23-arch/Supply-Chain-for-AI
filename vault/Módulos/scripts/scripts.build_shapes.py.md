---
tipo: "modulo"
capa: "Infraestructura"
ruta: "scripts/build_shapes.py"
lenguaje: "python"
lineas: 265
aliases: ["scripts/build_shapes.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# scripts/build_shapes.py

> Módulo · capa [[Capa Infraestructura]] · 265 líneas · `scripts/build_shapes.py`

## Para qué sirve

compila las formas SHACL a IR (docs/INFRA_OPERATIVA.md §3.3; paso 10).

## API pública

- `vocab_ttl()` _(línea 48)_
- `source_sha()` _(línea 84)_
- `shapes_graph()` _(línea 93)_
- `compile_ir(g=…)` _(línea 101)_
- `check(verbose=…)` _(línea 210)_
- `write()` _(línea 241)_
- `main(argv=…)` _(línea 254)_

**Internas** (empiezan con `_`): `_ttl_list`, `_read`

## Depende de

- [[core.__init__.py]] — importa `KHS`, `RULES`, `compact`, `ir_canonical_hash`
- [[core.decisions.py]] — importa `decisions`
- [[ontology.vocabulary.py]] — importa `vocabulary`

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

_Además lo importan 3 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_gates_conformance.py]]
- [[tests.test_gates_ir_fresh.py]]
- [[tests.test_import_shapes.py]]
