---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "engine/pickers.js"
lenguaje: "javascript"
lineas: 431
aliases: ["engine/pickers.js"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# engine/pickers.js

> Módulo · capa [[Capa Chat y agentes]] · 431 líneas · `engine/pickers.js`

## Para qué sirve

opciones FIJAS en vez de texto libre (pedido de Fabrizio 2026-10-05: "donde se escriban cosas fijas como tickers de empresas no quiero que te deje escribir sino que te vaya recomendando en base a lo que escribes y sean fixed options").

## API pública (globales que define)

`window.KhipuPick`

## Depende de

- [[engine.app_main.js]] — usa `LANG`, `NODE_BY_ID`
- [[engine.khipu_chat.js]] — usa `KhipuChat`
- [[engine.mascot.js]] — usa `KhipuMascot`
- [[engine.resolve.js]] — usa `KhipuResolve`
- [[nodes.crypto_intel.js]] — usa `CRYPTO_INTEL`
- [[nodes.crypto_intel2.js]] — usa `CRYPTO_INTEL`
- [[nodes.nodes_seed.js]] — usa `NODES`

Se carga en [[app.html]] en la posición **58 de 99** (línea 3166), después de [[engine.spacemonitor.js]] y antes de [[engine.committee.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 58)
- [[engine.clients.js]] — usa `KhipuPick`
- [[engine.cockpit.js]] — usa `KhipuPick`
- [[engine.command_center.js]] — usa `KhipuPick`
- [[engine.committee.js]] — usa `KhipuPick`

## Pruebas que lo cubren

- [[tests.test_khipus_os_chat.py]]
- [[tests.test_pickers.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (s) — CARTERA CONTEXTO, AGENTE QUIÉN RESPONDE (sw v225)]]
- [[Sesión 2026-10-05 (o) — AGENTES CON CHIP EN EL CHAT - EL COMITÉ DE CARTERA RESPONDE AHÍ]]
- [[Sesión 2026-10-05 (k) — OPCIONES FIJAS Y MENÚ - EN EL CHAT (sw v213)]]
