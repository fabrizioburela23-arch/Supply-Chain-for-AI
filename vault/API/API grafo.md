---
tipo: "api"
capa: "Ontología y grafo temporal"
rutas: 2
tags: ["capa/ontologia", "tipo/api"]
---

# API grafo

> 2 rutas · definidas en [[server.py]] · prefijo `/api/grafo`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/grafo/estado` | `grafo_estado` | [[server.py]] | [[engine.temporal-graph.js]] |
| `POST` | `/api/grafo/seed` | `grafo_seed` | [[server.py]] | [[engine.temporal-graph.js]] |
