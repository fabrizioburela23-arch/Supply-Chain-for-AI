---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-13"
ruta: "docs/ESTADO.md#L254"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-13 (i) — NEO4J RETIRADO (decisión #6 de Fabrizio) — sw v264

> Sesión de trabajo · `docs/ESTADO.md` línea 254 (23 líneas) · [[Índice de sesiones]]

## Resumen

\- HECHO POR FABRIZIO (2026-10-13): borró NEO4J_URI/USER/PASSWORD en Railway y activó «Wait for CI» (Railway → servicio → Settings → Source). Desde ahora un push a main despliega SOLO si .github/workflows/ci.yml pasa (G5-02 cerrado). - Fabrizio decidió: «si crees que es lo mejor quita neo4j» (BRECHAS §2 #6; ARQUITECTURA_V2: Postgres es la única base). Nadie leía Neo4j: solo recibía hechos (`POST /api/grafo/seed`) y el 🩺 probaba la conexión.

## Archivos que menciona

- [[Doc CLAUDE]]
- [[core.http.py]]
- [[Doc BRECHAS_V2]]
- [[Doc CIERRE_INFRA]]
- [[engine.temporal-graph.js]]
- [[server.py]]
- [[tests.test_cierre_infra.py]]
- [[tests.test_neo4j_retirado.py]]

← más antigua: [[Sesión 2026-10-13 (h) — PASO 24 - REPETIR DECISIONES (replay), IMPLEMENTACIONES RETENIDAS]] · más nueva: [[Sesión 2026-10-13 (j) — ESPACIO - VUELVEN LOS SATÉLITES (arreglo urgente) — sw v265]] →
