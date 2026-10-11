---
tipo: "api"
capa: "Cuantitativo (matrices, tensores, riesgo)"
rutas: 1
tags: ["capa/cuantitativo", "tipo/api"]
---

# API screener

> 1 rutas · definidas en [[server.py]] · prefijo `/api/screener`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/screener/growth` | `screener_growth` | [[server.py]] | [[engine.cockpit.js]], 2 pruebas |
