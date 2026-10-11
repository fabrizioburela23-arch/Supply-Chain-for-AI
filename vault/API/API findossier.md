---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 1
tags: ["capa/datos-vivo", "tipo/api"]
---

# API findossier

> 1 rutas · definidas en [[server.py]] · prefijo `/api/findossier`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/findossier/<ticker>` | `fin_dossier` | [[server.py]] | [[engine.cockpit.js]], [[engine.fincard.js]], [[engine.localcharts.js]], [[engine.termdata.js]], 2 pruebas |
