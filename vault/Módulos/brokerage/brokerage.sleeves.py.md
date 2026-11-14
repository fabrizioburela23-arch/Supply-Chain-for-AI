---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "brokerage/sleeves.py"
lenguaje: "python"
lineas: 360
aliases: ["brokerage/sleeves.py"]
tags: ["capa/dinero", "tipo/modulo"]
---

# brokerage/sleeves.py

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 360 líneas · `brokerage/sleeves.py`

## Para qué sirve

VARIAS CARTERAS sobre UNA cuenta de Alpaca (docs/CARTERAS_Y_AGENTES.md, fase 2).

## API pública

- `ledger(session, sleeve)` — {'cash', 'reserved', 'available', 'holdings': {sym: qty}, 'cost': {sym: usd}} de UNA cartera. _(línea 48)_
- `check_order(session, client_id, sleeve_id, symbol, side, notional=…, qty=…, price=…)` — → (ok, motivo_es, motivo_en). La cartera debe existir, estar activa y alcanzar (efectivo / acciones). _(línea 82)_
- `list_view(session, client_id, account=…, positions=…)` — Carteras activas + la «Principal» (lo no asignado) con valores en vivo de la cuenta. _(línea 130)_
- `unallocated_cash(session, client_id, account_cash)` _(línea 156)_
- `create(session, client_id, name, objective=…, alloc_usd=…, risk_profile=…, actor=…, account_cash=…)` _(línea 180)_
- `update(session, client_id, sleeve_id, patch, actor=…, account_cash=…)` _(línea 212)_
- `archive(session, client_id, sleeve_id, actor=…)` _(línea 246)_
- `sleeves_list()` _(línea 295)_
- `sleeves_create()` _(línea 315)_
- `sleeves_update(sleeve_id)` _(línea 336)_
- `sleeves_archive(sleeve_id)` _(línea 353)_

**Internas** (empiezan con `_`): `_f`, `_orders`, `_get`, `_check_sell`, `_view`, `_snap`, `_decide`, `_clean_text`, `_db`, `_no_db`, `_http`, `_actor`

## Depende de

- [[brokerage.models.py]] — importa `BrokerOrder`, `BrokerSleeve`
- [[brokerage.service.py]] — importa `service`
- [[core.decision_sites.py]] — importa `decision_sites`
- [[core.http.py]] — importa `rate_limit`
- [[core.identity.py]] — importa `identity`
- [[core.pin.py]] — importa `require_pin`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`

## Lo usan

- [[brokerage.service.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/trade/sleeves` | `sleeves_list` | [[engine.portfolios.js]], 1 prueba |
| `POST` | `/api/trade/sleeves` | `sleeves_create` | [[engine.portfolios.js]], 1 prueba |
| `PATCH` | `/api/trade/sleeves/<sleeve_id>` | `sleeves_update` | [[engine.portfolios.js]] |
| `POST` | `/api/trade/sleeves/<sleeve_id>/archive` | `sleeves_archive` | [[engine.portfolios.js]], 1 prueba |

Grupos: [[API trade]]

## Pruebas que lo cubren

- [[tests.test_broker_sleeves.py]]
- [[tests.test_order_single_path.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
