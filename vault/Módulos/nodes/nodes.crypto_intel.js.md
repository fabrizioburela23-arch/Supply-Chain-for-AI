---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/crypto_intel.js"
lenguaje: "javascript"
lineas: 405
aliases: ["nodes/crypto_intel.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/crypto_intel.js

> Datos · capa [[Capa Datos del catálogo]] · 405 líneas · `nodes/crypto_intel.js`

## Para qué sirve

Capa estática de inteligencia cripto (expediente jul-2026). Fuente: KHIPUS_CRIPTO_TOP50_EXPEDIENTE.md (snapshot CoinMarketCap, semana 6-12 jul 2026). Esta capa cualitativa (tesis, tokenomics, riesgos) debe refrescarse cada 3-6 meses; los datos dinámicos (precio, volumen, market cap) se jalan en vivo vía CoinGecko/CMC. Indexado por ID de CoinGecko; la UI también matchea por ticker como fallback.

## Qué datos contiene

- ~73 entradas con clave
- 25 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.CRYPTO_CATS`, `window.CRYPTO_INTEL`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **82 de 97** (línea 7941), después de [[engine.pricehist.js]] y antes de [[nodes.crypto_intel2.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 82)
- [[engine.crypto.js]] — usa `CRYPTO_CATS`, `CRYPTO_INTEL`
- [[engine.pickers.js]] — usa `CRYPTO_INTEL`

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-07-12 — Etapas I+J — Feedback 8 + Expediente Cripto (sw v76)]]
