---
tipo: "api"
capa: "Infraestructura"
rutas: 1
tags: ["capa/infraestructura", "tipo/api"]
---

# API diagnostics

> 1 rutas · definidas en [[server.py]] · prefijo `/api/diagnostics`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/diagnostics` | `diagnostics` | [[server.py]] | [[app.html]], [[core.ai_usage.py]], 1 prueba |
