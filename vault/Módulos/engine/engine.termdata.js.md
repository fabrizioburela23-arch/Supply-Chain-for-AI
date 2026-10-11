---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "engine/termdata.js"
lenguaje: "javascript"
lineas: 359
aliases: ["engine/termdata.js"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# engine/termdata.js

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 359 líneas · `engine/termdata.js`

## Para qué sirve

PANEL DE DATOS de la Terminal (feedback de Fabrizio: "te pedí que la terminal tuviera muchas más tablas" + "para muchas decía upstream 402 pero no sale nada, necesito ver la info de todos"). Columna derecha colapsable que se llena SOLA al abrir cualquier empresa (hook en _termLoadCell) con tablas reales: 1. FICHA — sector, país, fundada, empleados, ingresos, cap, NRS… 2. PERFIL — descripción y riesgo geográfico (LOCAL, para TODAS las empresas: nunca queda vacío aunque no haya API) 3. VALUACIÓN — P/E, EV/EBITDA, precio objetivo y ratings de analistas 4. FUNDAMENTALES— serie anual: crec. ingresos, margen bruto/FCF, ROE, D/E 5. CADENA — top proveedores y clientes con peso …

## API pública (globales que define)

`window.TermData`

## Depende de

- [[app.html]] — usa `BASE`, `LANG`, `LINKS`, `MKT`, `NODE_BY_ID`, `_termOpenTicker`, `computeNRS`, `fillLiveMeta`, `liveCapDot`, `sectorName`
- [[engine.explain.js]] — usa `explainChip`
- [[engine.fincard.js]] — usa `openFinCard`
- [[engine.xray.js]] — usa `openXRay`
- [[nodes.nodes_seed.js]] — usa `NODES`, `NODE_META`

Se carga en [[app.html]] en la posición **74 de 92** (línea 7924), después de [[engine.fincard.js]] y antes de [[engine.explain.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 74)
- [[app.html]] — usa `TermData`

## Endpoints que llama

- `GET /api/findossier/<ticker>` → [[server.py]] ([[API findossier]])
- `GET /api/fundamentals/<ticker>` → [[server.py]] ([[API fundamentals]])

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-03 (c) — TERMINAL REDISEÑADA + POP-UPS DE COMPRA-VENTA (sw v182)]]
- [[Sesión 2026-09-27 — La app en el TELÉFONO (sw v136)]]
- [[Sesión 2026-07-10 — modo máximo (feedback - perfeccionar Khipu, 555 empresas, vivo, 3D)]]
