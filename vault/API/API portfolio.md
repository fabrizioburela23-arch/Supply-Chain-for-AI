---
tipo: "api"
capa: "Dinero (carteras, trading, corretaje)"
rutas: 4
tags: ["capa/dinero", "tipo/api"]
---

# API portfolio

> 4 rutas · definidas en [[server.py]] · prefijo `/api/portfolio`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `POST` | `/api/portfolio/advice` | `portfolio_advice` | [[server.py]] | [[engine.cockpit.js]] |
| `POST` | `/api/portfolio/comment` | `portfolio_comment` | [[server.py]] | [[engine.cockpit.js]], 1 prueba |
| `POST` | `/api/portfolio/risk_report` | `portfolio_risk_report` | [[server.py]] | [[engine.riskreport.js]], 2 pruebas |
| `POST` | `/api/portfolio/vega_report` | `portfolio_vega_report` | [[server.py]] | [[engine.riskreport.js]], 1 prueba |
