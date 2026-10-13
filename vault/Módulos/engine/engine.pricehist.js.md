---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/pricehist.js"
lenguaje: "javascript"
lineas: 189
aliases: ["engine/pricehist.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/pricehist.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 189 líneas · `engine/pricehist.js`

## Para qué sirve

🩺 Sistema → «Historia de precios» (BRECHAS bloque 2: la memoria de los números). Muestra cuánta historia guarda Khipus (cierres diarios ajustados, tipo de cambio diario, fotos diarias de métricas y posiciones) y el progreso del relleno de 5 años. El relleno NUNCA es automático (decisión #3 sin responder): «Descargar 5 años (PIN)» lo arranca el operador por window._tradeFetch, con KhipuToast.confirm (nunca window.confirm); «Detener (PIN)» lo pausa (es reanudable). Textos ES/EN. API: window.KhipuPriceHistory.mount(containerId)

## API pública (globales que define)

`window.KhipuPriceHistory`

## Depende de

- [[app.html]] — usa `BASE`, `LANG`, `_tradeFetch`
- [[engine.explain.js]] — usa `explainChip`, `explainRegister`
- [[engine.toast.js]] — usa `KhipuToast`

Se carga en [[app.html]] en la posición **81 de 97** (línea 7940), después de [[engine.audit.js]] y antes de [[nodes.crypto_intel.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 81)
- [[app.html]] — usa `KhipuPriceHistory`

## Endpoints que llama

- `GET /api/prices/backfill` → [[core.prices_api.py]] ([[API prices]])
- `GET /api/prices/status` → [[core.prices_api.py]] ([[API prices]])
- `POST /api/prices/backfill/stop` → [[core.prices_api.py]] ([[API prices]])
- `POST /api/prices/backfill` → [[core.prices_api.py]] ([[API prices]])

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
