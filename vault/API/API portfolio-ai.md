---
tipo: "api"
capa: "Dinero (carteras, trading, corretaje)"
rutas: 3
tags: ["capa/dinero", "tipo/api"]
---

# API portfolio-ai

> 3 rutas · definidas en [[core.portfolio_ai.py]] · prefijo `/api/portfolio-ai`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `POST` | `/api/portfolio-ai/ask` | `ask_endpoint` | [[core.portfolio_ai.py]] | [[engine.portfolios.js]], 1 prueba |
| `POST` | `/api/portfolio-ai/propose` | `propose_endpoint` | [[core.portfolio_ai.py]] | [[engine.portfolios.js]], 1 prueba |
| `GET` | `/api/portfolio-ai/themes` | `themes_endpoint` | [[core.portfolio_ai.py]] | [[engine.portfolios.js]], 1 prueba |
