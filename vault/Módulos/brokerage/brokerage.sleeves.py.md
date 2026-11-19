---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "brokerage/sleeves.py"
lenguaje: "python"
lineas: 420
aliases: ["brokerage/sleeves.py"]
tags: ["capa/dinero", "tipo/modulo"]
---

# brokerage/sleeves.py

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 420 líneas · `brokerage/sleeves.py`

## Para qué sirve

VARIAS CARTERAS sobre UNA cuenta de Alpaca (docs/CARTERAS_Y_AGENTES.md, fase 2).

## API pública

- `ledger(session, sleeve)` — {'cash', 'reserved', 'available', 'holdings': {sym: qty}, 'cost': {sym: usd}} de UNA cartera. _(línea 48)_
- `check_order(session, client_id, sleeve_id, symbol, side, notional=…, qty=…, price=…)` — → (ok, motivo_es, motivo_en). La cartera debe existir, estar activa y alcanzar (efectivo / acciones). _(línea 82)_
- `list_view(session, client_id, account=…, positions=…)` — Carteras activas + la «Principal» (lo no asignado) con valores en vivo de la cuenta. _(línea 138)_
- `unallocated_cash(session, client_id, account_cash)` _(línea 164)_
- `create(session, client_id, name, objective=…, alloc_usd=…, risk_profile=…, actor=…, account_cash=…)` _(línea 188)_
- `update(session, client_id, sleeve_id, patch, actor=…, account_cash=…)` _(línea 220)_
- `archive(session, client_id, sleeve_id, actor=…)` _(línea 254)_
- `sleeves_list()` _(línea 303)_
- `sleeves_create()` _(línea 323)_
- `sleeves_update(sleeve_id)` _(línea 344)_
- `set_agent(session, client_id, sleeve_id, raw, actor=…)` — Guarda (o apaga) el agente de una cartera — policy.change 'broker.sleeve_agent' en el libro. _(línea 358)_
- `sleeves_agent_parse()` — Texto en palabras → configuración PROPUESTA (no guarda nada: guardar es el PATCH de abajo). _(línea 383)_
- `sleeves_agent_set(sleeve_id)` _(línea 398)_
- `sleeves_archive(sleeve_id)` _(línea 413)_

**Internas** (empiezan con `_`): `_f`, `_orders`, `_get`, `_check_sell`, `_view`, `_snap`, `_decide`, `_clean_text`, `_db`, `_no_db`, `_http`, `_actor`

## Depende de

- [[brokerage.models.py]] — importa `BrokerOrder`, `BrokerSleeve`
- [[brokerage.service.py]] — importa `service`
- [[core.decision_sites.py]] — importa `decision_sites`
- [[core.http.py]] — importa `_safe_ticker`, `rate_limit`
- [[core.identity.py]] — importa `identity`
- [[core.pin.py]] — importa `require_pin`
- [[core.sleeve_agents.py]] — importa `sleeve_agents`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`

## Lo usan

- [[brokerage.service.py]] — lo importa
- [[core.sleeve_agents.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/trade/sleeves` | `sleeves_list` | [[engine.portfolios.js]], 1 prueba |
| `POST` | `/api/trade/sleeves` | `sleeves_create` | [[engine.portfolios.js]], 1 prueba |
| `PATCH` | `/api/trade/sleeves/<sleeve_id>` | `sleeves_update` | [[engine.portfolios.js]] |
| `PATCH` | `/api/trade/sleeves/<sleeve_id>/agent` | `sleeves_agent_set` | [[engine.portfolios.js]], 1 prueba |
| `POST` | `/api/trade/sleeves/<sleeve_id>/archive` | `sleeves_archive` | [[engine.portfolios.js]], 1 prueba |
| `POST` | `/api/trade/sleeves/agent/parse` | `sleeves_agent_parse` | [[engine.portfolios.js]], 1 prueba |

Grupos: [[API trade]]

## Pruebas que lo cubren

- [[tests.test_broker_sleeves.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_sleeve_agents.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
