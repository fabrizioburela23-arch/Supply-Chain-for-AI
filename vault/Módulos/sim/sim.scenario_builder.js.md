---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "sim/scenario_builder.js"
lenguaje: "javascript"
lineas: 262
aliases: ["sim/scenario_builder.js"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# sim/scenario_builder.js

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 262 líneas · `sim/scenario_builder.js`

## Para qué sirve

Constructor de seeds para las simulaciones (Khipu Finance) Genera el "seed" textual que alimenta a los motores de simulación con contexto realista: geopolítica + sentimiento social + precedentes históricos + perfiles de agentes. Incluye 5 escenarios predefinidos listos para el demo.

## API pública (globales que define)

`window.ScenarioBuilder`, `window.buildLiveReportContext`, `window.buildScenarioSeed`

De nivel superior (globales del script): `HISTORICAL_PRECEDENTS`, `STRUCTURAL_BACKGROUND`, `_sbJSON`, `_sbValuation`, `buildGeopoliticalContext`, `buildPlayers`, `buildSocialContext`

## Depende de

- [[app.html]] — usa `BASE`, `NODE_BY_ID`, `quotePx`
- [[nodes.nodes_seed.js]] — usa `NODE_META`
- [[nodes.private_valuations.js]] — usa `PRIVATE_VALUATIONS`

Se carga en [[app.html]] en la posición **86 de 91** (línea 7936), después de [[engine.command_center.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 86)
- [[app.html]] — usa `ScenarioBuilder`, `buildLiveReportContext`
- [[engine.voice.js]] — usa `ScenarioBuilder`

## Endpoints que llama

- `GET /api/company/live/<ticker>` → [[server.py]] ([[API company]])
- `GET /api/news/gdelt/<company_name>` → [[server.py]] ([[API news]])
- `GET /api/world/brief` → [[core.world.py]] ([[API world]])
- `GET /api/world/gpr` → [[core.world.py]] ([[API world]])
- `GET /api/world/policy` → [[core.world.py]] ([[API world]])

## Pruebas que lo cubren

- [[tests.test_scenario_live.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (bb) — SIMULACIÓN IA SIMPLE CON DATOS EN VIVO (sw v235)]]
- [[Sesión 2026-10-05 (z) — SIMULACIÓN CON CONTEXTO EN VIVO + RÓTULOS DE ORIGEN (sw v233)]]
