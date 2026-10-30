---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/ticket.js"
lenguaje: "javascript"
lineas: 250
aliases: ["engine/ticket.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/ticket.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 250 líneas · `engine/ticket.js`

## Para qué sirve

MODO TICKET del panel de trading (2026-10-30, pedido de Fabrizio). Dos modos en el MISMO panel (se elige arriba del botón; queda guardado en localStorage 'kh_trade_mode'): · 'broker' (por defecto) — como siempre: confirmar + PIN → Alpaca (papel 🧪 o real 🔴). No cambia nada. · 'ticket' — NO envía NADA a ningún bróker: arma el ticket de la orden (qué, cuánto, a qué precio, por qué ojo), le pasa revisiones LOCALES sobre tu cartera y lo deja listo para copiar a Interactive Brokers (o cualquier otro). Después «Ya lo ejecuté» anota lo que de verdad pasó en tu cartera (engine/pfstore.js: la misma cartera de Mercado, Terminal y chat). Regla de oro del dinero (CLAUDE.md): este …

## API pública (globales que define)

`window.KhipuTicket`, `window._tpRelabel`, `window.openTradePanelFn`, `window.submitTradePanelOrder`

## Depende de

- [[engine.app_main.js]] — usa `LANG`, `MKT`, `NODE_BY_ID`, `quoteIsLive`, `quotePx`, `savePos`
- [[engine.app_trade_panel.js]] — usa `_tpRefreshPositions`

Se carga en [[app.html]] en la posición **101 de 104** (línea 3556), después de [[engine.app_trade_panel.js]] y antes de [[engine.app_preflight.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 101)
- [[app.html]] — usa `submitTradePanelOrder`

## Pruebas que lo cubren

- [[tests.test_ticket_mode.py]]
