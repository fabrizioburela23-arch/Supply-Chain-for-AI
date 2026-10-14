---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/graph3d.js"
lenguaje: "javascript"
lineas: 1227
aliases: ["engine/graph3d.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/graph3d.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 1.227 líneas · `engine/graph3d.js`

## Para qué sirve

Motor de visualización 3D Three.js para Khipu Finance Renderiza los 450+ nodos como esferas en el espacio, con tamaño por market cap, links de colores, raycast para hover/click, y highlight de stress-test en 3D.

## API pública (globales que define)

`window.KhipuGraph3D`, `window.__bixbyEnergy`, `window._graph3d_updateLiveColors`

## Depende de

- [[engine.app_coordinator.js]] — usa `_diag`, `khipuGraph3D`
- [[engine.app_main.js]] — usa `LINKS`, `NODE_BY_ID`, `_tickerWarnings`, `computeNRS`, `computeNodeRadius`, `getCatColorHex`, `getLinkColorHex`, `jumpTo`, `quotePx`, `selectNode`
- [[engine.geo_coords.js]] — usa `GeoCoords`, `KhipuCountries`
- [[nodes.nodes_seed.js]] — usa `CATS`

## Lo usan

- [[engine.app_coordinator.js]] — usa `KhipuGraph3D`
- [[engine.app_main.js]] — usa `_graph3d_updateLiveColors`
- [[engine.app_coordinator.js]] — lo nombra por su ruta

## Pruebas que lo cubren

- [[tests.test_cleanup_client.py]]
- [[tests.test_countries.py]]
- [[tests.test_server_smoke.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-28 — X-Ray pulido (sw v139)]]
- [[Sesión 2026-09-21 — Limpieza estructural - Track A Fase 2 + Track B completos]]
- [[Sesión 2026-08-01 — Prompt frontend+IA (Cowork) - Tracks C y D implementados]]
- [[Sesión 2026-07-12 — Etapas I+J — Feedback 8 + Expediente Cripto (sw v76)]]
- [[Sesión 2026-07-12 — Etapa L — Universo 2D como motor PRINCIPAL (sw v78)]]
