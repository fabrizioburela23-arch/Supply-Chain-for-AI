---
tipo: "modulo"
capa: "Otros"
ruta: "scripts/research_batch.py"
lenguaje: "python"
lineas: 460
aliases: ["scripts/research_batch.py"]
tags: ["capa/otros", "tipo/modulo"]
---

# scripts/research_batch.py

> Módulo · capa [[Capa Otros]] · 460 líneas · `scripts/research_batch.py`

## Para qué sirve

investiga empresas con la API de Claude (búsqueda web) y escribe fichas khipus.company/1.

## API pública

- `norm(s)` _(línea 57)_
- `hint_of(name)` — 'AECC Aviation Power' → 'AECCAviationPower' (el estilo de id del catálogo). _(línea 62)_
- `known_entities()` — {norm(nombre o id): (id, nombre)} del catálogo + todas las fichas de los lotes 2-6 (para no repetir y para que la IA use el id exacto de la … _(línea 86)_
- `make_list()` _(línea 107)_
- `make_enrich_list()` — Empresas que YA están en Khipus pero casi sin conexiones: del catálogo, las de ≤ 2 vínculos de flujo; de los lotes 2-6, las de < 3 vínculos … _(línea 143)_
- `system_prompt()` _(línea 195)_
- `user_prompt(row, n)` _(línea 216)_
- `enrich_prompt(row, n)` — La empresa YA existe en Khipus: el objetivo son los VÍNCULOS (y lo que le falte a la ficha), no repetirla. _(línea 227)_
- clase `Spend` _(línea 245)_
- `research_one(client, args, system, row, n, spend)` _(línea 288)_
- `main(argv=…)` _(línea 376)_

**Internas** (empiezan con `_`): `_records`, `_solid`, `_rules`, `_text`, `_json`, `_more_links`

## Depende de

- [[core.ai.py]] — importa `_extract_json`
- [[ontology.company_import.py]] — importa `company_import`
- [[ontology.vocabulary.py]] — importa `vocabulary`
- [[data.categories.json]] — lo nombra por su ruta
- [[data.grafo_v0.json]] — lo nombra por su ruta

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Pruebas que lo cubren

- [[tests.test_research_batch.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
