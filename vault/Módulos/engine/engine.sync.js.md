---
tipo: "modulo"
capa: "Infraestructura"
ruta: "engine/sync.js"
lenguaje: "javascript"
lineas: 139
aliases: ["engine/sync.js"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# engine/sync.js

> Módulo · capa [[Capa Infraestructura]] · 139 líneas · `engine/sync.js`

## Para qué sirve

SINCRONIZACIÓN ENTRE DISPOSITIVOS (carteras, perfil, posiciones)

## API pública (globales que define)

`window.KhipuSync`

## Depende de

- [[engine.app_main.js]] — usa `BASE`
- [[engine.mascot.js]] — usa `KhipuAgentPrefs`
- [[engine.portfolios.js]] — usa `KhipuPortfolios`

Se carga en [[app.html]] en la posición **65 de 101** (línea 3175), después de [[engine.pfreports.js]] y antes de [[engine.clients.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 65)
- [[engine.pfcommittee.js]] — usa `KhipuSync`

## Endpoints que llama

- `GET,PUT /api/user-state` → [[core.portfolio_reports_api.py]] ([[API user-state]])

## Pruebas que lo cubren

- [[tests.test_khipus_os_chat.py]]
- [[tests.test_one_portfolio_store.py]]
- [[tests.test_portfolio_persist.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-15 — b — REVISIÓN DE UN SOLO LUGAR - NADA SE PIERDE ENTRE DISPOSITIVOS]]
- [[Sesión 2026-10-05 (l) — CARTERAS QUE DESAPARECÍAN + COMITÉ DE CARTERA REGISTRADO (sw v214)]]
- [[Sesión 2026-10-03 (g) — SINCRONIZACIÓN ENTRE DISPOSITIVOS (sw v184)]]
- [[Sesión 2026-10-03 — VISIÓN PRÓXIMA ETAPA (pedido, NO es parte de Phase 3)]]
