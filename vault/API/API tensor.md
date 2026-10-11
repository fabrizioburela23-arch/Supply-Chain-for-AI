---
tipo: "api"
capa: "Cuantitativo (matrices, tensores, riesgo)"
rutas: 5
tags: ["capa/cuantitativo", "tipo/api"]
---

# API tensor

> 5 rutas · definidas en [[matrix.tensor_api.py]] · prefijo `/api/tensor`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/tensor/eval` | `tensor_eval` | [[matrix.tensor_api.py]] | — |
| `GET` | `/api/tensor/node/<path:nid>` | `tensor_node` | [[matrix.tensor_api.py]] | [[engine.oswindows.js]], [[engine.xray.js]], 3 pruebas |
| `GET` | `/api/tensor/rank` | `tensor_rank` | [[matrix.tensor_api.py]] | 1 prueba |
| `GET` | `/api/tensor/status` | `tensor_status` | [[matrix.tensor_api.py]] | — |
| `POST` | `/api/tensor/suggest` | `tensor_suggest` | [[matrix.tensor_api.py]] | 1 prueba |
