---
tipo: "modulo"
capa: "Datos del catálogo"
ruta: "scripts/build_instrument_review.py"
lenguaje: "python"
lineas: 119
aliases: ["scripts/build_instrument_review.py"]
tags: ["capa/datos-catalogo", "tipo/modulo"]
---

# scripts/build_instrument_review.py

> Módulo · capa [[Capa Datos del catálogo]] · 119 líneas · `scripts/build_instrument_review.py`

## Para qué sirve

genera docs/REVISION_INSTRUMENTOS.md (BRECHAS_V2 L3-13, decisión #9).

## API pública

- `render(nodes)` _(línea 34)_
- `main(argv=…)` _(línea 98)_

**Internas** (empiezan con `_`): `_row`, `_nodes`

## Depende de

- [[core.instruments.py]] — importa `instruments`
- [[data.grafo_v0.json]] — lo nombra por su ruta

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
