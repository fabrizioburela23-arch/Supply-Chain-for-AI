---
tipo: "api"
capa: "Investigación"
rutas: 2
tags: ["capa/investigacion", "tipo/api"]
---

# API deep

> 2 rutas · definidas en [[server.py]] · prefijo `/api/deep`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `POST` | `/api/deep/analyze` | `deep_analyze` | [[server.py]] | [[engine.cockpit.js]], 1 prueba |
| `GET` | `/api/deep/status` | `deep_status` | [[server.py]] | [[engine.cockpit.js]], 1 prueba |
