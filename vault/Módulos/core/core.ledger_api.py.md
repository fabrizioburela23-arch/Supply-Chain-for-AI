---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/ledger_api.py"
lenguaje: "python"
lineas: 359
aliases: ["core/ledger_api.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/ledger_api.py

> Módulo · capa [[Capa Infraestructura]] · 359 líneas · `core/ledger_api.py`

## Para qué sirve

lectura del libro de decisiones: /api/ledger/\* (docs/INFRA_OPERATIVA.md §2.9; paso 6).

## API pública

- `ledger_status()` _(línea 82)_
- `ledger_decisions()` _(línea 103)_
- `ledger_decision(decision_id)` _(línea 135)_
- `ledger_verify()` _(línea 163)_
- `ledger_anchor()` — Ancla diaria PÚBLICA: SOLO la cabeza de la cadena (ningún contenido). Sin ancla todavía → anchor:null. _(línea 188)_
- `ledger_chain()` _(línea 206)_
- `ledger_chain_ack()` — Reconocer la cadena rota (PIN estricto, persona). Cuerpo: {note?, break_id?}. _(línea 221)_
- `ledger_replay(decision_id)` _(línea 272)_
- `ledger_why(decision_id)` _(línea 304)_
- `ledger_audit()` _(línea 327)_

**Internas** (empiezan con `_`): `_db`, `_unavailable`, `_operator`, `_require_operator`, `_err`, `_uuid_or_400`, `_iso_arg`

## Depende de

- [[core.ai_calls.py]] — importa `ai_calls`
- [[core.decisions.py]] — importa `decisions`, `stats`
- [[core.http.py]] — importa `rate_limit`
- [[core.identity.py]] — importa `KINDS`, `identity`
- [[core.ledger.py]] — importa `ledger`
- [[core.pin.py]] — importa `pin`
- [[core.replay.py]] — importa `replay`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 3 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/ledger/anchor` | `ledger_anchor` | [[scripts.fetch_ledger_anchor.py]], 1 prueba |
| `GET` | `/api/ledger/audit` | `ledger_audit` | [[engine.audit.js]], 1 prueba |
| `GET` | `/api/ledger/chain` | `ledger_chain` | 1 prueba |
| `POST` | `/api/ledger/chain_ack` | `ledger_chain_ack` | 1 prueba |
| `GET` | `/api/ledger/decision/<decision_id>` | `ledger_decision` | 2 pruebas |
| `GET` | `/api/ledger/decisions` | `ledger_decisions` | 2 pruebas |
| `GET,POST` | `/api/ledger/replay/<decision_id>` | `ledger_replay` | [[engine.audit.js]], 2 pruebas |
| `GET` | `/api/ledger/status` | `ledger_status` | 2 pruebas |
| `GET` | `/api/ledger/verify` | `ledger_verify` | 1 prueba |
| `GET` | `/api/ledger/why/<decision_id>` | `ledger_why` | [[engine.audit.js]], 2 pruebas |

Grupos: [[API ledger]]

## Pruebas que lo cubren

- [[tests.test_cierre_defectos.py]]
- [[tests.test_ledger_anchor.py]]
- [[tests.test_ledger_core.py]]
- [[tests.test_ledger_privacy.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_replay_determinism.py]]
