---
tipo: "modulo"
capa: "Ontología y grafo temporal"
ruta: "engine/hypergraph.js"
lenguaje: "javascript"
lineas: 273
aliases: ["engine/hypergraph.js"]
tags: ["capa/ontologia", "tipo/modulo"]
---

# engine/hypergraph.js

> Módulo · capa [[Capa Ontología y grafo temporal]] · 273 líneas · `engine/hypergraph.js`

## Para qué sirve

Hipergrafos temporales agénticos para Khipu Finance Una hiper-arista conecta MÚLTIPLES nodos a la vez (un evento que afecta a N empresas) y tiene fecha + severidad. Se renderiza como una esfera translúcida que envuelve al cluster afectado en el grafo 3D, con un timeline reproducible.

## API pública (globales que define)

`window.TemporalHypergraph`

## Depende de

- [[engine.app_main.js]] — usa `DataLayer`, `NODE_BY_ID`, `getCatColorHex`

## Lo usan

- [[engine.app_coordinator.js]] — usa `TemporalHypergraph`
- [[engine.app_coordinator.js]] — lo nombra por su ruta

## Pruebas que lo cubren

- [[tests.test_cleanup_client.py]]
- [[tests.test_server_smoke.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-07 — REDISEÑO MAYOR — mapa único con capas + motor de matrices]]
