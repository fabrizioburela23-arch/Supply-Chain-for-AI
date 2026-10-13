---
tipo: "api"
capa: "Infraestructura"
rutas: 4
tags: ["capa/infraestructura", "tipo/api"]
---

# API ledger

> 4 rutas · definidas en [[core.ledger_api.py]] · prefijo `/api/ledger`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/ledger/decision/<decision_id>` | `ledger_decision` | [[core.ledger_api.py]] | 2 pruebas |
| `GET` | `/api/ledger/decisions` | `ledger_decisions` | [[core.ledger_api.py]] | 2 pruebas |
| `GET` | `/api/ledger/status` | `ledger_status` | [[core.ledger_api.py]] | 1 prueba |
| `GET` | `/api/ledger/verify` | `ledger_verify` | [[core.ledger_api.py]] | 1 prueba |
