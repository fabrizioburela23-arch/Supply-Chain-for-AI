---
tipo: "api"
capa: "Cuantitativo (matrices, tensores, riesgo)"
rutas: 1
tags: ["capa/cuantitativo", "tipo/api"]
---

# API options

> 1 rutas · definidas en [[server.py]] · prefijo `/api/options`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/options/chain/<symbol>` | `options_chain` | [[server.py]] | [[engine.riskreport.js]], 1 prueba |
