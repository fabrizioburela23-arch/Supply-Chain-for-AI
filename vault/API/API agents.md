---
tipo: "api"
capa: "Chat y agentes"
rutas: 1
tags: ["capa/chat-agentes", "tipo/api"]
---

# API agents

> 1 rutas · definidas en [[core.agents_api.py]] · prefijo `/api/agents`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/agents/profiles` | `agent_profiles_endpoint` | [[core.agents_api.py]] | [[engine.oswindows.js]], 3 pruebas |
