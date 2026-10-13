---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/ledger_api.py"
lenguaje: "python"
lineas: 232
aliases: ["core/ledger_api.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/ledger_api.py

> Módulo · capa [[Capa Infraestructura]] · 232 líneas · `core/ledger_api.py`

## Para qué sirve

lectura del libro de decisiones: /api/ledger/\* (docs/INFRA_OPERATIVA.md §2.9; paso 6).

## API pública

- `ledger_status()` _(línea 74)_
- `ledger_decisions()` _(línea 89)_
- `ledger_decision(decision_id)` _(línea 121)_
- `ledger_verify()` _(línea 149)_
- `ledger_anchor()` — Ancla diaria PÚBLICA: SOLO la cabeza de la cadena (ningún contenido). Sin ancla todavía → anchor:null. _(línea 172)_
- `ledger_chain()` _(línea 190)_
- `ledger_chain_ack()` — Reconocer la cadena rota (PIN estricto, persona). Cuerpo: {note?, break_id?}. _(línea 205)_

**Internas** (empiezan con `_`): `_db`, `_unavailable`, `_operator`, `_require_operator`, `_err`

## Depende de

- [[core.decisions.py]] — importa `decisions`, `stats`
- [[core.http.py]] — importa `rate_limit`
- [[core.identity.py]] — importa `identity`
- [[core.ledger.py]] — importa `ledger`
- [[core.pin.py]] — importa `pin`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 3 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/ledger/anchor` | `ledger_anchor` | [[scripts.fetch_ledger_anchor.py]], 1 prueba |
| `GET` | `/api/ledger/chain` | `ledger_chain` | 1 prueba |
| `POST` | `/api/ledger/chain_ack` | `ledger_chain_ack` | 1 prueba |
| `GET` | `/api/ledger/decision/<decision_id>` | `ledger_decision` | 2 pruebas |
| `GET` | `/api/ledger/decisions` | `ledger_decisions` | 2 pruebas |
| `GET` | `/api/ledger/status` | `ledger_status` | 2 pruebas |
| `GET` | `/api/ledger/verify` | `ledger_verify` | 1 prueba |

Grupos: [[API ledger]]

## Pruebas que lo cubren

- [[tests.test_ledger_anchor.py]]
- [[tests.test_ledger_core.py]]
- [[tests.test_ledger_privacy.py]]
- [[tests.test_ops_identity.py]]
