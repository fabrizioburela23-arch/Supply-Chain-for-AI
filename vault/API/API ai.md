---
tipo: "api"
capa: "Infraestructura"
rutas: 4
tags: ["capa/infraestructura", "tipo/api"]
---

# API ai

> 4 rutas · definidas en [[server.py]] · prefijo `/api/ai`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `POST` | `/api/ai/analyze` | `ai_analyze` | [[server.py]] | [[app.html]], [[core.ai_usage.py]], [[engine.brief.js]], [[engine.temporal-graph.js]], 1 prueba |
| `GET` | `/api/ai/debug` | `ai_debug` | [[server.py]] | 1 prueba |
| `GET` | `/api/ai/usage` | `ai_usage_report` | [[server.py]] | [[engine.aispend.js]], 1 prueba |
| `POST` | `/api/ai/usage/limits` | `ai_usage_limits` | [[server.py]] | [[engine.aispend.js]], 2 pruebas |
