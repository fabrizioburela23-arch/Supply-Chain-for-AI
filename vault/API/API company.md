---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 3
tags: ["capa/datos-vivo", "tipo/api"]
---

# API company

> 3 rutas · definidas en [[server.py]] · prefijo `/api/company`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/company/live/<ticker>` | `company_live` | [[server.py]] | [[app.html]], [[engine.fincard.js]], [[sim.scenario_builder.js]], 1 prueba |
| `GET` | `/api/company/research/<ticker>` | `company_research` | [[server.py]] | [[app.html]] |
| `GET` | `/api/company/valuation/<path:name>` | `company_valuation_news` | [[server.py]] | [[engine.fincard.js]] |
