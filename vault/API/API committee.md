---
tipo: "api"
capa: "Comité"
rutas: 14
tags: ["capa/comite", "tipo/api"]
---

# API committee

> 14 rutas · definidas en [[research.committee_api.py]] · prefijo `/api/committee`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/committee/board` | `board_route` | [[research.committee_api.py]] | [[engine.brief.js]], [[engine.committee.js]], [[engine.oswindows.js]], 3 pruebas |
| `POST` | `/api/committee/board/refresh` | `board_refresh` | [[research.committee_api.py]] | [[engine.committee.js]], 2 pruebas |
| `GET` | `/api/committee/calibration` | `calibration` | [[research.committee_api.py]] | [[engine.research.js]], 2 pruebas |
| `GET` | `/api/committee/clients` | `clients` | [[research.committee_api.py]] | [[engine.committee.js]], 2 pruebas |
| `GET` | `/api/committee/entity/<entity_id>` | `entity` | [[research.committee_api.py]] | [[engine.committee.js]], [[engine.oswindows.js]], 3 pruebas |
| `GET` | `/api/committee/memo/<memo_id>` | `memo` | [[research.committee_api.py]] | [[engine.committee.js]], [[engine.oswindows.js]], 3 pruebas |
| `POST` | `/api/committee/memo/<memo_id>/approve` | `approve` | [[research.committee_api.py]] | [[engine.committee.js]], [[engine.oswindows.js]], 3 pruebas |
| `POST` | `/api/committee/memo/<memo_id>/reject` | `reject` | [[research.committee_api.py]] | [[engine.committee.js]], [[engine.oswindows.js]], 2 pruebas |
| `POST` | `/api/committee/outcomes/evaluate` | `evaluate` | [[research.committee_api.py]] | [[engine.committee.js]], 1 prueba |
| `GET` | `/api/committee/outcomes/recent` | `outcomes_recent` | [[research.committee_api.py]] | [[engine.committee.js]], 1 prueba |
| `POST` | `/api/committee/portfolio` | `portfolio_committee` | [[research.committee_api.py]] | [[engine.pfcommittee.js]], 1 prueba |
| `POST` | `/api/committee/portfolio/ask` | `portfolio_ask` | [[research.committee_api.py]] | [[engine.khipu_chat.js]], 1 prueba |
| `POST` | `/api/committee/run` | `run` | [[research.committee_api.py]] | [[engine.committee.js]], 1 prueba |
| `GET` | `/api/committee/track-record` | `track_record` | [[research.committee_api.py]] | [[engine.committee.js]], [[engine.research.js]], 2 pruebas |
