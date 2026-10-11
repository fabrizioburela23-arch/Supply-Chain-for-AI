---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 1
tags: ["capa/datos-vivo", "tipo/api"]
---

# API dossier

> 1 rutas · definidas en [[server.py]] · prefijo `/api/dossier`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/dossier/<ticker>` | `dossier` | [[server.py]] | [[app.html]], 1 prueba |
