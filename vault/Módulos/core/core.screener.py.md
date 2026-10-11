---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "core/screener.py"
lenguaje: "python"
lineas: 185
aliases: ["core/screener.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# core/screener.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 185 líneas · `core/screener.py`

## Para qué sirve

Screener de crecimiento explosivo: /api/screener/\*.

## API pública

- `ensure_warmer()` _(línea 123)_
- `screen_growth(top=…)` — Ranking de señales de crecimiento explosivo. Score: 0.5·r20 + 0.2·r60 + 0.3·r5 (aceleración reciente pesa) + bonus estructural (+6 si … _(línea 151)_

**Internas** (empiezan con `_`): `_load_universe`, `_momentum`, `_next_stale`, `_warmer_loop`, `_pagerank_ranks`

## Depende de

- [[matrix.api.py]] — importa `_TTL_CACHE`
- [[data.grafo_v0.json]] — lo nombra por su ruta

## Lo usan

- [[server.py]] — lo importa

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
