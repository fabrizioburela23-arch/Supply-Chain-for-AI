---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/loading.js"
lenguaje: "javascript"
lineas: 159
aliases: ["engine/loading.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/loading.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 159 líneas · `engine/loading.js`

## Para qué sirve

Sistema de animaciones de carga por NIVEL DE ESPERA. Pedido de Fabrizio (2026-07-14): "que todo lo que tarde tenga una animación de carga adecuada; hay tipos de animación según cuánto se espera que tarde".

## API pública (globales que define)

`window.KhipuLoading`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **26 de 93** (línea 7818), después de [[nodes.merge_graph.js]] y antes de [[engine.toast.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 26)
- [[engine.cockpit.js]] — usa `KhipuLoading`

## Pruebas que lo cubren

- [[tests.test_overnight2_fixer_review.py]]
- [[tests.test_overnight3_toast_tokens.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
