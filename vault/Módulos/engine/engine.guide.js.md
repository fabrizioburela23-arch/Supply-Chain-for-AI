---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/guide.js"
lenguaje: "javascript"
lineas: 271
aliases: ["engine/guide.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/guide.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 271 líneas · `engine/guide.js`

## Para qué sirve

pestaña "❓ Guía": explica la app en lenguaje simple. Sin jerga técnica. Expone window.initGuiaTab (mismo patrón que initTKGTab). Actualizada 2026-07-12 (pedido de Fabrizio: "la guía está desactualizada"). 2026-09-28: BILINGÜE (regla del proyecto) y al día — 949 empresas, ⏱ en el mapa, 📡 feed, actualizaciones silenciosas (ya no hay aviso "Nueva versión"). 2026-09-28 (tarde): toda empresa tiene 📊 Dossier y qué parte es EN VIVO. 2026-10-04: 🪟 Escritorio Khipu (ventanas dentro de la Cabina). 2026-10-03: Pizarra, Sala del comité, Mi cartera (perfil/diagnóstico/reportes/noticias/pregúntale), simulación estructural, 💰 Gasto IA y avisos de compra/venta. Se reconstruye si cambia el …

## API pública (globales que define)

`window.initGuiaTab`

## Depende de

- [[engine.app_main.js]] — usa `LANG`, `LINKS`, `NODE_BY_ID`
- [[nodes.nodes_seed.js]] — usa `NODES`

Se carga en [[app.html]] en la posición **50 de 97** (línea 3041), después de [[engine.khipu_lang.js]] y antes de [[engine.xray.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 50)
- [[engine.app_main.js]] — usa `initGuiaTab`
- [[engine.cockpit.js]] — usa `initGuiaTab`

## Pruebas que lo cubren

- [[tests.test_committee_os_narr.py]]
- [[tests.test_live_labels_misc.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-09 — EL COMITÉ ENTRA A KHIPUS OS (sw v250)]]
- [[Sesión 2026-10-03 (f) — PANEL DE TRADING BILINGÜE Y MÓVIL + APROBACIÓN DEL COMITÉ CON]]
