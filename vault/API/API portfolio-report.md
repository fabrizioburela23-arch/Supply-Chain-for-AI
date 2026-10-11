---
tipo: "api"
capa: "Dinero (carteras, trading, corretaje)"
rutas: 6
tags: ["capa/dinero", "tipo/api"]
---

# API portfolio-report

> 6 rutas · definidas en [[core.portfolio_reports_api.py]] · prefijo `/api/portfolio-report`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `DELETE,GET` | `/api/portfolio-report/<rid>` | `one_report` | [[core.portfolio_reports_api.py]] | [[engine.pfcommittee.js]], [[engine.pfreports.js]], 2 pruebas |
| `POST` | `/api/portfolio-report/ask` | `ask` | [[core.portfolio_reports_api.py]] | [[engine.pfcommittee.js]], [[engine.pfreports.js]], 2 pruebas |
| `POST` | `/api/portfolio-report/generate` | `generate` | [[core.portfolio_reports_api.py]] | [[engine.pfcommittee.js]], [[engine.pfreports.js]], 2 pruebas |
| `GET` | `/api/portfolio-report/list` | `list_reports` | [[core.portfolio_reports_api.py]] | [[engine.pfcommittee.js]], [[engine.pfreports.js]], 2 pruebas |
| `POST` | `/api/portfolio-report/watch` | `save_watch` | [[core.portfolio_reports_api.py]] | [[engine.pfcommittee.js]], [[engine.pfreports.js]], 2 pruebas |
| `GET` | `/api/portfolio-report/watches` | `list_watches` | [[core.portfolio_reports_api.py]] | [[engine.pfcommittee.js]], [[engine.pfreports.js]], 2 pruebas |
