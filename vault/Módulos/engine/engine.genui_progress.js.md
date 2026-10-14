---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/genui_progress.js"
lenguaje: "javascript"
lineas: 198
aliases: ["engine/genui_progress.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/genui_progress.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 198 líneas · `engine/genui_progress.js`

## Para qué sirve

RESPUESTAS VISUALES PROGRESIVAS (F3, docs/CHAT_UI_GENERATIVA.md §6): el motor del chat que pinta los bloques provisionales y hace ATERRIZAR la respuesta final sobre ellos.

## API pública (globales que define)

`window.KhipuGenUIProgress`

## Depende de

- [[engine.genui.js]] — usa `KhipuGenUI`
- [[engine.khipu_chat.js]] — usa `KhipuChat`

## Lo usan

- [[engine.khipu_chat.js]] — usa `KhipuGenUIProgress`

## Pruebas que lo cubren

- [[tests.test_genui_browser.py]]
- [[tests.test_genui_client_static.py]]
- [[tests.test_genui_f3_client_static.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-14 (b) — LOTE J - SERVIDOR A 5.000 + CHAT PROGRESIVO (F3) + revisión — sw]]
