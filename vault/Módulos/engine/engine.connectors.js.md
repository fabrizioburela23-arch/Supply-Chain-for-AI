---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/connectors.js"
lenguaje: "javascript"
lineas: 166
aliases: ["engine/connectors.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/connectors.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 166 líneas · `engine/connectors.js`

## Para qué sirve

🧩 CONECTORES (tus apps) en Khipus OS (2026-11-26, pedido de Fabrizio: «algo que se conecte a todo, sin un MCP por cada cosa»). Puerta única: Composio (servidor: core/connectors.py + core/connectors_api.py).

## API pública (globales que define)

`window.KhipuConnectors`

## Depende de

- [[app.html]] — usa `_tradeFetch`
- [[engine.app_main.js]] — usa `BASE`, `LANG`
- [[engine.toast.js]] — usa `KhipuToast`

Se carga en [[app.html]] en la posición **96 de 108** (línea 3250), después de [[engine.a2ui.js]] y antes de [[engine.desktop.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 96)
- [[engine.cockpit.js]] — usa `KhipuConnectors`

## Endpoints que llama

- `GET /api/connectors/pending` → [[core.connectors_api.py]] ([[API connectors]])
- `GET /api/connectors/status` → [[core.connectors_api.py]] ([[API connectors]])
- `POST /api/connectors/confirm` → [[core.connectors_api.py]] ([[API connectors]])
- `POST /api/connectors/discard` → [[core.connectors_api.py]] ([[API connectors]])
- `POST /api/connectors/link` → [[core.connectors_api.py]] ([[API connectors]])

## Pruebas que lo cubren

- [[tests.test_connectors.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
