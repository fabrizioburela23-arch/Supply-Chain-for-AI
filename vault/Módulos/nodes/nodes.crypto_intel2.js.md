---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/crypto_intel2.js"
lenguaje: "javascript"
lineas: 489
aliases: ["nodes/crypto_intel2.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/crypto_intel2.js

> Datos · capa [[Capa Datos del catálogo]] · 489 líneas · `nodes/crypto_intel2.js`

## Para qué sirve

Capa estática de inteligencia cripto (lote 2: secciones B, F, G, H, I, J) Fuente: KHIPUS_CRIPTO_TOP50_EXPEDIENTE.md (snapshot jul-2026, CoinMarketCap semana 6-12 jul 2026). Esta capa es ESTÁTICA (tesis, tokenomics, riesgos): refrescar cada 3-6 meses. Los datos dinámicos (precio, volumen, market cap) se jalan en vivo vía CoinGecko — no viven aquí. Indexado por ID de CoinGecko; la UI también matchea por ticker como fallback. NO redefinir CRYPTO_CATS aquí — vive en crypto_intel.js.

## Qué datos contiene

- ~93 entradas con clave
- 34 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.CRYPTO_INTEL`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **83 de 97** (línea 3140), después de [[nodes.crypto_intel.js]] y antes de [[engine.crypto.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 83)
- [[engine.crypto.js]] — usa `CRYPTO_INTEL`
- [[engine.pickers.js]] — usa `CRYPTO_INTEL`

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-07-12 — Etapas I+J — Feedback 8 + Expediente Cripto (sw v76)]]
