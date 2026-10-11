---
tipo: "api"
capa: "Infraestructura"
rutas: 2
tags: ["capa/infraestructura", "tipo/api"]
---

# API diag

> 2 rutas · definidas en [[server.py]] · prefijo `/api/diag`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `POST` | `/api/diag` | `client_diag` | [[server.py]] | [[app.html]] |
| `GET` | `/api/diag/recent` | `client_diag_recent` | [[server.py]] | 1 prueba |
