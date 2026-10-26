---
tipo: "modulo"
capa: "Otros"
ruta: "scripts/links_to_ficha.py"
lenguaje: "python"
lineas: 171
aliases: ["scripts/links_to_ficha.py"]
tags: ["capa/otros", "tipo/modulo"]
---

# scripts/links_to_ficha.py

> Módulo · capa [[Capa Otros]] · 171 líneas · `scripts/links_to_ficha.py`

## Para qué sirve

vínculos investigados (JSON de los agentes) → fichas khipus.company/1 «de solo vínculos».

## API pública

- `build(files, min_conf=…, today=…)` — → (fichas, resumen). Una ficha por empresa con ≥ 1 vínculo bueno; mismo vínculo repetido se deja una vez. _(línea 85)_
- `main(argv=…)` _(línea 150)_

**Internas** (empiezan con `_`): `_clean_link`

## Depende de

- [[core.import_normalize.py]] — importa `iso2_of`
- [[ontology.company_import.py]] — importa `company_import`
- [[data.grafo_v0.json]] — lo nombra por su ruta

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Pruebas que lo cubren

- [[tests.test_links_to_ficha.py]]
