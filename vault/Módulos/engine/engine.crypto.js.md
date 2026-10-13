---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "engine/crypto.js"
lenguaje: "javascript"
lineas: 989
aliases: ["engine/crypto.js"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# engine/crypto.js

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 989 líneas · `engine/crypto.js`

## Para qué sirve

Pestaña ₿ Cripto (Fase 1 módulo de datos + Expediente). - Datos VIVOS: /api/crypto/\* (server → core/providers/coingecko.py). - Capa ESTÁTICA: window.CRYPTO_INTEL + window.CRYPTO_CATS (nodes/crypto_intel\*.js, expediente jul-2026, refrescar cada 3-6 meses). Vistas (elección de Fabrizio 2026-07-12, maqueta "Burbujas vivas"): 🫧 Burbujas — canvas con física suave: tamaño = market cap, color = 24h%, anillo rojo punteado = ⚠ del expediente. Tap = tarjeta con "Ver ficha". ☰ Lista — top 100 con filtros por tesis del expediente (badges 📋/⚠). Detalle — gráfico 90d + caja 💼 Operar (broker Alpaca, /api/trade/\*) + Expediente Khipus de 6 bloques + banner ⚠. Bilingüe ES/EN (regla del …

## API pública (globales que define)

`window.KhipuCrypto`

## Depende de

- [[app.html]] — usa `LANG`, `_tradeErrText`, `_tradeFetch`, `_tradeOrderAmbiguous`, `_tradeOrderId`, `_tradeOrderIsDup`, `_tradeOrderSettle`, `_tradePinStored`, `t`
- [[engine.cockpit.js]] — usa `BixbyCockpit`
- [[engine.resolve.js]] — usa `_surface`
- [[engine.toast.js]] — usa `KhipuToast`
- [[nodes.crypto_intel.js]] — usa `CRYPTO_CATS`, `CRYPTO_INTEL`
- [[nodes.crypto_intel2.js]] — usa `CRYPTO_INTEL`

Se carga en [[app.html]] en la posición **82 de 95** (línea 7947), después de [[nodes.crypto_intel2.js]] y antes de [[engine.portfolios.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 82)
- [[app.html]] — usa `KhipuCrypto`
- [[engine.cockpit.js]] — usa `KhipuCrypto`

## Endpoints que llama

- `GET /api/crypto/<coin_id>/history` → [[server.py]] ([[API crypto]])
- `GET /api/crypto/<coin_id>` → [[server.py]] ([[API crypto]])
- `GET /api/crypto/markets` → [[server.py]] ([[API crypto]])
- `GET /api/trade/crypto/assets` → [[server.py]] ([[API trade]])
- `POST /api/crypto/analyze` → [[server.py]] ([[API crypto]])
- `POST /api/trade/order` → [[server.py]] ([[API trade]])

## Pruebas que lo cubren

- [[tests.test_client_hardening.py]]
- [[tests.test_live_labels_misc.py]]
- [[tests.test_ops_identity.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-03 (c) — TERMINAL REDISEÑADA + POP-UPS DE COMPRA-VENTA (sw v182)]]
- [[Sesión 2026-07-12 — Etapa H — Feedback 7 - explicabilidad + regla bilingüe + cripto]]
- [[Sesión 2026-07-12 — Etapas I+J — Feedback 8 + Expediente Cripto (sw v76)]]
- [[Sesión 2026-07-12 — Etapa K — Burbujas cripto + universo 2D + caso Opera (sw v77)]]
- [[Sesión 2026-07-13 — Etapa M — Trading cripto en papel, integrado en Khipu (sw v80)]]
