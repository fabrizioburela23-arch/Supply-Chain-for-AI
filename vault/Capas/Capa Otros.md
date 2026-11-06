---
tipo: "capa"
capa: "Otros"
archivos: 3
tags: ["capa/otros", "tipo/capa"]
---

# Capa Otros

> Archivos que la tabla de capas todavía no clasifica (se reportan para asignarles capa).

**3 archivos · 858 líneas.** Volver al [[00 Mapa de Khipus]].

## Archivos

- [[scripts.research_batch.py]] — 532 líneas · investiga empresas con la API de Claude (búsqueda web) y escribe fichas khipus.company/1.
- [[scripts.links_to_ficha.py]] — 200 líneas · vínculos investigados (JSON de los agentes) → fichas khipus.company/1 «de solo vínculos».
- [[scripts.eval_chat.py]] — 126 líneas · Examen de oro del chat Khipu (stdlib, sin dependencias).

## Conexiones con otras capas

| Dirección | Capa | Conexiones |
|---|---|---|
| usa a | [[Capa Ontología y grafo temporal]] | 4 |
| usa a | [[Capa Datos del catálogo]] | 3 |
| usa a | [[Capa Infraestructura]] | 2 |
| usa a | [[Capa Chat y agentes]] | 1 |
