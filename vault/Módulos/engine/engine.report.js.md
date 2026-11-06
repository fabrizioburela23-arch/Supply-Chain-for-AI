---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/report.js"
lenguaje: "javascript"
lineas: 104
aliases: ["engine/report.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/report.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 104 líneas · `engine/report.js`

## Para qué sirve

📄 INFORME de cualquier respuesta del chat (2026-11-06, pedido de Fabrizio: «que Khipus pueda hacer informes como ese de forma nativa»).

## API pública (globales que define)

`window.KhipuReport`

## Depende de

- [[engine.app_main.js]] — usa `LANG`
- [[engine.toast.js]] — usa `KhipuToast`

Se carga en [[app.html]] en la posición **93 de 105** (línea 3247), después de [[engine.khipu_chat.js]] y antes de [[engine.desktop.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 93)
- [[engine.khipu_chat.js]] — usa `KhipuReport`

## Pruebas que lo cubren

- [[tests.test_genui_sim_report.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
