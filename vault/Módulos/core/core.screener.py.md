---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "core/screener.py"
lenguaje: "python"
lineas: 194
aliases: ["core/screener.py"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# core/screener.py

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 194 líneas · `core/screener.py`

## Para qué sirve

Screener de crecimiento explosivo: /api/screener/\*.

## API pública

- `ensure_warmer()` _(línea 123)_
- `screen_growth(top=…)` — Ranking de señales de crecimiento explosivo. Score: 0.5·r20 + 0.2·r60 + 0.3·r5 (aceleración reciente pesa) + bonus estructural (+6 si … _(línea 160)_

**Internas** (empiezan con `_`): `_load_universe`, `_momentum`, `_next_stale`, `_warmer_loop`, `_pagerank_ranks`

## Depende de

- [[core.__init__.py]] — importa `registry`
- [[matrix.api.py]] — importa `_TTL_CACHE`
- [[data.grafo_v0.json]] — lo nombra por su ruta

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_hot_review_fixes.py]]
