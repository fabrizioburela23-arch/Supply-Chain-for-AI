---
tipo: "api"
capa: "Ontología y grafo temporal"
rutas: 2
tags: ["capa/ontologia", "tipo/api"]
---

# API vocabulary

> 2 rutas · definidas en [[server.py]] · prefijo `/api/vocabulary`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/vocabulary` | `api_vocabulary` | [[server.py]] | 3 pruebas |
| `GET` | `/api/vocabulary/unknown` | `api_vocabulary_unknown` | [[server.py]] | — |
