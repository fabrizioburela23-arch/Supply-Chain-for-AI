---
tipo: "api"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
rutas: 3
tags: ["capa/datos-vivo", "tipo/api"]
---

# API news

> 3 rutas · definidas en [[core.portfolio_reports_api.py]], [[server.py]] · prefijo `/api/news`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/news/<ticker>` | `company_news` | [[server.py]] | [[app.html]], [[engine.fincard.js]], [[engine.pfreports.js]], [[engine.temporal-graph.js]], [[engine.voice.js]], 1 prueba |
| `GET` | `/api/news/gdelt/<company_name>` | `news_gdelt` | [[server.py]] | [[app.html]], [[engine.fincard.js]], [[engine.temporal-graph.js]], [[sim.scenario_builder.js]], 1 prueba |
| `POST` | `/api/news/portfolio` | `news_portfolio` | [[core.portfolio_reports_api.py]] | [[app.html]], [[engine.pfreports.js]], [[engine.temporal-graph.js]], [[engine.voice.js]] |
