---
tipo: "api"
capa: "Chat y agentes"
rutas: 2
tags: ["capa/chat-agentes", "tipo/api"]
---

# API decide

> 2 rutas · definidas en [[core.decide_api.py]] · prefijo `/api/decide`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/decide/shadow` | `shadow` | [[core.decide_api.py]] | [[engine.aispend.js]] |
| `GET` | `/api/decide/status` | `status` | [[core.decide_api.py]] | [[engine.aispend.js]], 1 prueba |
