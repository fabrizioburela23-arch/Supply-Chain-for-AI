---
tipo: "capa"
capa: "Otros"
archivos: 4
tags: ["capa/otros", "tipo/capa"]
---

# Capa Otros

> Archivos que la tabla de capas todavía no clasifica (se reportan para asignarles capa).

**4 archivos · 970 líneas.** Volver al [[00 Mapa de Khipus]].

## Archivos

- [[scripts.research_batch.py]] — 532 líneas · investiga empresas con la API de Claude (búsqueda web) y escribe fichas khipus.company/1.
- [[scripts.links_to_ficha.py]] — 200 líneas · vínculos investigados (JSON de los agentes) → fichas khipus.company/1 «de solo vínculos».
- [[scripts.eval_chat.py]] — 126 líneas · Examen de oro del chat Khipu (stdlib, sin dependencias).
- [[scripts.backtest_forecast.py]] — 112 líneas · Backtest: simulación propia de Khipus (core/price_sim) vs TimesFM 2.5 vs ingenuo (precio de hoy). Para cada acción y cada fecha de corte (cada 5 días …

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| usa a | [[Capa Ontología y grafo temporal]] | 4 |
| usa a | [[Capa Datos del catálogo]] | 3 |
| usa a | [[Capa Infraestructura]] | 3 |
| usa a | [[Capa Chat y agentes]] | 1 |
