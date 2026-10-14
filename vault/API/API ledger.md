---
tipo: "api"
capa: "Infraestructura"
rutas: 10
tags: ["capa/infraestructura", "tipo/api"]
---

# API ledger

> 10 rutas · definidas en [[core.ledger_api.py]] · prefijo `/api/ledger`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/ledger/anchor` | `ledger_anchor` | [[core.ledger_api.py]] | [[scripts.fetch_ledger_anchor.py]], 1 prueba |
| `GET` | `/api/ledger/audit` | `ledger_audit` | [[core.ledger_api.py]] | [[engine.audit.js]], 1 prueba |
| `GET` | `/api/ledger/chain` | `ledger_chain` | [[core.ledger_api.py]] | 1 prueba |
| `POST` | `/api/ledger/chain_ack` | `ledger_chain_ack` | [[core.ledger_api.py]] | 1 prueba |
| `GET` | `/api/ledger/decision/<decision_id>` | `ledger_decision` | [[core.ledger_api.py]] | 2 pruebas |
| `GET` | `/api/ledger/decisions` | `ledger_decisions` | [[core.ledger_api.py]] | 2 pruebas |
| `GET,POST` | `/api/ledger/replay/<decision_id>` | `ledger_replay` | [[core.ledger_api.py]] | [[engine.audit.js]], 2 pruebas |
| `GET` | `/api/ledger/status` | `ledger_status` | [[core.ledger_api.py]] | 2 pruebas |
| `GET` | `/api/ledger/verify` | `ledger_verify` | [[core.ledger_api.py]] | 1 prueba |
| `GET` | `/api/ledger/why/<decision_id>` | `ledger_why` | [[core.ledger_api.py]] | [[engine.audit.js]], [[engine.genui.js]], 2 pruebas |
