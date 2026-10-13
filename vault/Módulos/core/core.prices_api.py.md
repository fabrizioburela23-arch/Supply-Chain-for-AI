---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/prices_api.py"
lenguaje: "python"
lineas: 125
aliases: ["core/prices_api.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/prices_api.py

> Módulo · capa [[Capa Infraestructura]] · 125 líneas · `core/prices_api.py`

## Para qué sirve

/api/prices/\* y /api/instruments/\* (BRECHAS bloque 2: la memoria de los números). Nunca /v1/\*.

## API pública

- `prices_status()` _(línea 29)_
- `prices_eod(symbol)` _(línea 36)_
- `prices_backfill_state()` _(línea 61)_
- `prices_backfill_start()` _(línea 68)_
- `prices_backfill_stop()` _(línea 100)_
- `instruments_review()` _(línea 118)_

## Depende de

- [[core.decisions.py]] — importa `LedgerUnavailable`
- [[core.http.py]] — importa `_safe_ticker`, `rate_limit`
- [[core.identity.py]] — importa `identity`
- [[core.instruments.py]] — importa `instruments`
- [[core.pin.py]] — importa `pin`
- [[core.prices_store.py]] — importa `prices_store`
- [[core.risk_report.py]] — importa `fetch_history`, `history_meta`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/instruments/review` | `instruments_review` | 1 prueba |
| `GET` | `/api/prices/backfill` | `prices_backfill_state` | [[engine.pricehist.js]], 1 prueba |
| `POST` | `/api/prices/backfill` | `prices_backfill_start` | [[engine.pricehist.js]], 1 prueba |
| `POST` | `/api/prices/backfill/stop` | `prices_backfill_stop` | [[engine.pricehist.js]] |
| `GET` | `/api/prices/eod/<path:symbol>` | `prices_eod` | — |
| `GET` | `/api/prices/status` | `prices_status` | [[engine.pricehist.js]], 1 prueba |

Grupos: [[API instruments]], [[API prices]]

## Pruebas que lo cubren

- [[tests.test_prices_eod.py]]
