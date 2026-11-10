---
tipo: "modulo"
capa: "Otros"
ruta: "scripts/backtest_forecast.py"
lenguaje: "python"
lineas: 112
aliases: ["scripts/backtest_forecast.py"]
tags: ["capa/otros", "tipo/modulo"]
---

# scripts/backtest_forecast.py

> Módulo · capa [[Capa Otros]] · 112 líneas · `scripts/backtest_forecast.py`

## Para qué sirve

Backtest: simulación propia de Khipus (core/price_sim) vs TimesFM 2.5 vs ingenuo (precio de hoy). Para cada acción y cada fecha de corte (cada 5 días hábiles del último ~2 años) cada modelo solo ve el pasado y pronostica el cierre a 21 días hábiles (1 mes). Se compara con lo que pasó de verdad.

## API pública

- `load(path)` _(línea 28)_
- `ours(sym, hist)` _(línea 41)_
- `pinball(y, q, tau)` _(línea 50)_
- `score(rows)` _(línea 54)_
- `evaluate(q, y)` _(línea 63)_
- `main(paths)` _(línea 69)_

## Depende de

- [[core.price_sim.py]] — importa `price_sim`

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
