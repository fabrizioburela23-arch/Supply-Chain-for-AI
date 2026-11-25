---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/a2ui.js"
lenguaje: "javascript"
lineas: 286
aliases: ["engine/a2ui.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/a2ui.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 286 líneas · `engine/a2ui.js`

## Para qué sirve

LECTOR A2UI v1.0 de Khipus OS (2026-11-25, pedido de Fabrizio: «interfaz interactiva lo más avanzada posible, con futuro, rápida, útil y adaptable»).

## API pública (globales que define)

`window.KhipuA2UI`

## Depende de

- [[engine.app_main.js]] — usa `LANG`
- [[engine.genui.js]] — usa `KhipuGenUI`

Se carga en [[app.html]] en la posición **95 de 107** (línea 3249), después de [[engine.uiprefs.js]] y antes de [[engine.desktop.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 95)
- [[engine.khipu_chat.js]] — usa `KhipuA2UI`

## Pruebas que lo cubren

- [[tests.test_a2ui.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
