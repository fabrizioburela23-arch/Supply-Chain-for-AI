---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-13"
ruta: "docs/ESTADO.md#L12"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-13 (i) — NEO4J RETIRADO (decisión #6 de Fabrizio) — sw v264

> Sesión de trabajo · `docs/ESTADO.md` línea 12 (20 líneas) · [[Índice de sesiones]]

## Resumen

\- Fabrizio decidió: «si crees que es lo mejor quita neo4j» (BRECHAS §2 #6; ARQUITECTURA_V2: Postgres es la única base). Nadie leía Neo4j: solo recibía hechos (`POST /api/grafo/seed`) y el 🩺 probaba la conexión. - Borrado: en server.py la lectura de `NEO4J_\*`, `_neo4j_available`, `_temporal_mode`, `_get_neo4j_driver`, `_neo4j_add_fact`, `_FACT_CYPHER`, `_neo4j_estado_cache` y `POST /api/grafo/seed`; `NEO4J_\*` de las listas de

## Archivos que menciona

- [[Doc CLAUDE]]
- [[core.http.py]]
- [[Doc BRECHAS_V2]]
- [[Doc CIERRE_INFRA]]
- [[engine.temporal-graph.js]]
- [[server.py]]
- [[tests.test_cierre_infra.py]]
- [[tests.test_neo4j_retirado.py]]

← más antigua: [[Sesión 2026-10-13 (h) — PASO 24 - REPETIR DECISIONES (replay), IMPLEMENTACIONES RETENIDAS]]
