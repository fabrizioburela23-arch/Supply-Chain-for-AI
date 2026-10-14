---
tipo: "modulo"
capa: "Voz"
ruta: "engine/orb.js"
lenguaje: "javascript"
lineas: 396
aliases: ["engine/orb.js"]
tags: ["capa/voz", "tipo/modulo"]
---

# engine/orb.js

> Módulo · capa [[Capa Voz]] · 396 líneas · `engine/orb.js`

## Para qué sirve

BixbyOrb: el orbe de voz de Khipu.

## API pública (globales que define)

`window.BixbyOrb`

## Depende de

- [[engine.app_main.js]] — usa `LANG`

Se carga en [[app.html]] en la posición **35 de 99** (línea 3092), después de [[engine.resolve.js]] y antes de [[engine.trade.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 35)
- [[engine.cockpit.js]] — usa `BixbyOrb`
- [[engine.voice.js]] — usa `BixbyOrb`

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-07-13 — Etapa O — Khipus Finance AI - 9 frentes + rebrand + Cabina inicial]]
