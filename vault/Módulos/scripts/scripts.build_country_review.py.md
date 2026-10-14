---
tipo: "modulo"
capa: "Datos del catálogo"
ruta: "scripts/build_country_review.py"
lenguaje: "python"
lineas: 310
aliases: ["scripts/build_country_review.py"]
tags: ["capa/datos-catalogo", "tipo/modulo"]
---

# scripts/build_country_review.py

> Módulo · capa [[Capa Datos del catálogo]] · 310 líneas · `scripts/build_country_review.py`

## Para qué sirve

LISTA DE REVISIÓN DE PAÍSES para Fabrizio (lote 2026-10-14) + gemela JS.

## API pública

- `analyze(nodes=…, rows=…)` — Todo lo que el documento cuenta, como datos (lo usa tests/test_countries.py). _(línea 102)_
- `render(a)` _(línea 144)_
- `render_js_line()` — El bloque JS (varias líneas de ≤ ~120 caracteres para que el diff se lea; el contenido es el JSON de js_table). _(línea 250)_
- `update_js(write=…)` _(línea 267)_
- `main(argv=…)` _(línea 280)_

**Internas** (empiezan con `_`): `_load_nodes`, `_load_csv`, `_esc`, `_lbl`, `_src`, `_nrs_key_now`, `_nrs_key_canonical`, `_nrs_key_of_map`, `_nrs_changes`

## Depende de

- [[core.countries.py]] — importa `countries`
- [[core.world.py]] — importa `world`
- [[data.grafo_v0.json]] — lo nombra por su ruta

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_countries.py]]
