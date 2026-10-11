---
tipo: "api"
capa: "Investigación"
rutas: 10
tags: ["capa/investigacion", "tipo/api"]
---

# API research

> 10 rutas · definidas en [[research.api.py]], [[server.py]] · prefijo `/api/research`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/research/activity` | `activity` | [[research.api.py]] | [[engine.research.js]], 2 pruebas |
| `GET` | `/api/research/agents` | `agents` | [[research.api.py]] | — |
| `GET` | `/api/research/budget` | `budget` | [[research.api.py]] | — |
| `GET` | `/api/research/claims/<claim_id>` | `claim_why` | [[research.api.py]] | [[engine.research.js]], 2 pruebas |
| `POST` | `/api/research/deep` | `research_deep` | [[server.py]] | [[core.ai_usage.py]], [[engine.cockpit.js]], 2 pruebas |
| `GET` | `/api/research/entity/<entity_id>` | `entity` | [[research.api.py]] | [[engine.research.js]], 3 pruebas |
| `POST` | `/api/research/events` | `events` | [[research.api.py]] | — |
| `GET` | `/api/research/health` | `health` | [[research.api.py]] | [[research.health.py]], 1 prueba |
| `POST` | `/api/research/jobs` | `create` | [[research.api.py]] | [[engine.committee.js]], [[engine.pfcommittee.js]], [[engine.research.js]], 2 pruebas |
| `GET` | `/api/research/jobs/<job_id>` | `job` | [[research.api.py]] | [[engine.committee.js]], [[engine.research.js]], 1 prueba |
