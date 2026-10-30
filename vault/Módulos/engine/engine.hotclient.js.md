---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "engine/hotclient.js"
lenguaje: "javascript"
lineas: 485
aliases: ["engine/hotclient.js"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# engine/hotclient.js

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 485 líneas · `engine/hotclient.js`

## Para qué sirve

EL cliente de las vistas rápidas del servidor (window.KhipuHot) INFRA_OPERATIVA §4.6-§4.7 (paso 13, 2026-10-13): en el navegador NO queda ningún motor de contagio. Toda cifra de impacto que se ve (X-Ray, Cabina, simulación en vivo, voz, Insights, brief, Second Brain, banner de colapso del mapa, sala de guerra) sale de UN solo kernel: matrix.engine.propagate en el servidor, servido por /api/hot/\* (Postgres si hay DATABASE_URL; si no, el snapshot data/grafo_v0.json con el MISMO código — `view.source` lo dice). Así la misma caída da el mismo número en todas las pantallas.

## API pública (globales que define)

_No define globales (código encapsulado)._

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **31 de 104** (línea 3117), después de [[engine.toast.js]] y antes de [[engine.agents_registry.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 31)

**Rutas que nombra y no existen en el servidor** (¿restos viejos?): `/api/hot/card/`, `/api/hot/chokepoints`, `/api/hot/factors`, `/api/hot/impact/`, `/api/hot/nrs`, `/api/hot/scenario`, `/api/hot/scenario_pnl`, `/api/hot/status`

## Pruebas que lo cubren

- [[tests.test_genui_browser.py]]
- [[tests.test_genui_rivals.py]]
- [[tests.test_hot_contract.py]]
- [[tests.test_khipus_os_perf.py]]
- [[tests.test_lotej_review_fixes.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_one_portfolio_store.py]]
- [[tests.test_review_infra_c.py]]
- [[tests.test_scenario_pnl.py]]
- [[tests.test_scenario_pnl_browser.py]]
- [[tests.test_voice_os_client.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (c) — INFRAESTRUCTURA OPERATIVA, PASOS 7, 9, 10 y 13]]
