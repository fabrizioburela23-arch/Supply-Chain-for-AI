---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/ledger_api.py"
lenguaje: "python"
lineas: 160
aliases: ["core/ledger_api.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/ledger_api.py

> Módulo · capa [[Capa Infraestructura]] · 160 líneas · `core/ledger_api.py`

## Para qué sirve

lectura del libro de decisiones: /api/ledger/\* (docs/INFRA_OPERATIVA.md §2.9; paso 6).

## API pública

- `ledger_status()` _(línea 69)_
- `ledger_decisions()` _(línea 84)_
- `ledger_decision(decision_id)` _(línea 116)_
- `ledger_verify()` _(línea 144)_

**Internas** (empiezan con `_`): `_db`, `_unavailable`, `_operator`, `_require_operator`, `_err`

## Depende de

- [[core.decisions.py]] — importa `decisions`, `stats`
- [[core.http.py]] — importa `rate_limit`
- [[core.ledger.py]] — importa `ledger`
- [[core.pin.py]] — importa `pin`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 3 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/ledger/decision/<decision_id>` | `ledger_decision` | 2 pruebas |
| `GET` | `/api/ledger/decisions` | `ledger_decisions` | 2 pruebas |
| `GET` | `/api/ledger/status` | `ledger_status` | 1 prueba |
| `GET` | `/api/ledger/verify` | `ledger_verify` | 1 prueba |

Grupos: [[API ledger]]

## Pruebas que lo cubren

- [[tests.test_ledger_core.py]]
- [[tests.test_ledger_privacy.py]]
- [[tests.test_ops_identity.py]]
