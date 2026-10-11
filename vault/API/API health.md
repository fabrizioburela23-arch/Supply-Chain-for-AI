---
tipo: "api"
capa: "Infraestructura"
rutas: 1
tags: ["capa/infraestructura", "tipo/api"]
---

# API health

> 1 rutas · definidas en [[server.py]] · prefijo `/api/health`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/health` | `health` | [[server.py]] | [[app.html]], [[core.ai_usage.py]], 4 pruebas |
