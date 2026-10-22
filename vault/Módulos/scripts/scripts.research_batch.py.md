---
tipo: "modulo"
capa: "Otros"
ruta: "scripts/research_batch.py"
lenguaje: "python"
lineas: 336
aliases: ["scripts/research_batch.py"]
tags: ["capa/otros", "tipo/modulo"]
---

# scripts/research_batch.py

> Módulo · capa [[Capa Otros]] · 336 líneas · `scripts/research_batch.py`

## Para qué sirve

investiga empresas con la API de Claude (búsqueda web) y escribe fichas khipus.company/1.

## API pública

- `norm(s)` _(línea 51)_
- `hint_of(name)` — 'AECC Aviation Power' → 'AECCAviationPower' (el estilo de id del catálogo). _(línea 56)_
- `known_entities()` — {norm(nombre o id): (id, nombre)} del catálogo + todas las fichas de los lotes 2-6 (para no repetir y para que la IA use el id exacto de la … _(línea 80)_
- `make_list()` _(línea 101)_
- `system_prompt()` _(línea 140)_
- `user_prompt(row, n)` _(línea 161)_
- clase `Spend` _(línea 172)_
- `research_one(client, args, system, row, n, spend)` _(línea 215)_
- `main(argv=…)` _(línea 268)_

**Internas** (empiezan con `_`): `_records`, `_rules`, `_text`, `_json`

## Depende de

- [[core.ai.py]] — importa `_extract_json`
- [[ontology.company_import.py]] — importa `company_import`
- [[data.categories.json]] — lo nombra por su ruta
- [[data.grafo_v0.json]] — lo nombra por su ruta

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Pruebas que lo cubren

- [[tests.test_research_batch.py]]
