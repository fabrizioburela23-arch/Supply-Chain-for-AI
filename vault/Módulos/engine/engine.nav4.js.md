---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/nav4.js"
lenguaje: "javascript"
lineas: 118
aliases: ["engine/nav4.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/nav4.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 118 líneas · `engine/nav4.js`

## Para qué sirve

NAVEGACIÓN DE 4 PESTAÑAS (simplificación pedida por Fabrizio) Las 10 pestañas se agrupan bajo 4 primarias: 🗺️ Mapa → map · geo · space · tkg · simulation 📈 Mercado → market 💡 Insights → analysis · canvas · terminal ❓ Guía → guia NO toca switchTab ni los paneles: los sub-modos siguen siendo botones .tab con data-tab (los cablea el código existente). Este módulo solo pinta la barra primaria + muestra la fila de sub-modos del grupo activo. La fila secundaria se oculta cuando el grupo tiene un solo modo (Mercado, Guía).

## API pública (globales que define)

`window._nav4Wrapped`, `window.switchTab`

## Depende de

- [[app.html]] — usa `activeTab`, `switchTab`

Se carga en [[app.html]] en la posición **72 de 93** (línea 7911), después de [[engine.matrixview.js]] y antes de [[engine.localcharts.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 72)

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-27 — La app en el TELÉFONO (sw v136)]]
