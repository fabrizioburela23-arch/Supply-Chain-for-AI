---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "engine/clients.js"
lenguaje: "javascript"
lineas: 1060
aliases: ["engine/clients.js"]
tags: ["capa/dinero", "tipo/modulo"]
---

# engine/clients.js

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 1.060 líneas · `engine/clients.js`

## Para qué sirve

👥 CLIENTES E INVERSIÓN (corretaje multi-cliente vía Alpaca).

## API pública (globales que define)

`window.KhipuClients`

## Depende de

- [[app.html]] — usa `_tradeFetch`, `_tradePinStored`
- [[engine.app_main.js]] — usa `LANG`
- [[engine.explain.js]] — usa `explainChip`, `explainRegister`
- [[engine.mascot.js]] — usa `KhipuMascot`
- [[engine.pickers.js]] — usa `KhipuPick`
- [[engine.toast.js]] — usa `KhipuToast`, `khipuActor`

Se carga en [[app.html]] en la posición **67 de 103** (línea 3177), después de [[engine.sync.js]] y antes de [[engine.mcpconnect.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 67)
- [[app.html]] — usa `KhipuClients`
- [[engine.cockpit.js]] — usa `KhipuClients`
- [[engine.committee.js]] — usa `KhipuClients`
- [[engine.khipu_lang.js]] — usa `KhipuClients`
- [[engine.mcpconnect.js]] — usa `KhipuClients`

## Endpoints que llama

- `GET /api/brokerage/approvals` → [[brokerage.api.py]] ([[API brokerage]])
- `GET /api/brokerage/clients/<client_id>/account` → [[brokerage.api.py]] ([[API brokerage]])
- `GET /api/brokerage/clients/<client_id>/audit` → [[brokerage.api.py]] ([[API brokerage]])
- `GET /api/brokerage/clients/<client_id>` → [[brokerage.api.py]] ([[API brokerage]])
- `GET /api/brokerage/clients` → [[brokerage.api.py]] ([[API brokerage]])
- `GET /api/brokerage/orders` → [[brokerage.api.py]] ([[API brokerage]])
- `GET /api/brokerage/status/detail` → [[brokerage.api.py]] ([[API brokerage]])
- `GET /api/brokerage/status` → [[brokerage.api.py]] ([[API brokerage]])
- `PATCH /api/brokerage/clients/<client_id>` → [[brokerage.api.py]] ([[API brokerage]])
- `POST /api/brokerage/approvals/<preview_id>/approve` → [[brokerage.api.py]] ([[API brokerage]])
- `POST /api/brokerage/approvals/<preview_id>/reject` → [[brokerage.api.py]] ([[API brokerage]])
- `POST /api/brokerage/clients/<client_id>/credentials` → [[brokerage.api.py]] ([[API brokerage]])
- `POST /api/brokerage/clients/<client_id>/oauth/start` → [[brokerage.api.py]] ([[API brokerage]])
- `POST /api/brokerage/clients/<client_id>/sync` → [[brokerage.api.py]] ([[API brokerage]])
- `POST /api/brokerage/clients` → [[brokerage.api.py]] ([[API brokerage]])
- `POST /api/brokerage/orders/<order_id>/cancel` → [[brokerage.api.py]] ([[API brokerage]])
- `POST /api/brokerage/orders/<preview_id>/confirm` → [[brokerage.api.py]] ([[API brokerage]])
- `POST /api/brokerage/orders/preview` → [[brokerage.api.py]] ([[API brokerage]])

## Pruebas que lo cubren

- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_overnight_ui_dossier_clients.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-10-03 (c) — TERMINAL REDISEÑADA + POP-UPS DE COMPRA-VENTA (sw v182)]]
- [[Sesión 2026-09-30 — PHASE 3 + WORLD MONITOR + CORRETAJE + MCP + ENDURECIMIENTO (sw v170)]]
