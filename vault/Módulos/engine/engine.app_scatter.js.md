---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/app_scatter.js"
lenguaje: "javascript"
lineas: 281
aliases: ["engine/app_scatter.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/app_scatter.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 281 líneas · `engine/app_scatter.js`

## Para qué sirve

KHIPU FINANCE — Scatter 3D Semántico con Medidores Botón 📊: posiciona empresas en ejes semánticos + panel de medidores interactivo

## API pública (globales que define)

`window._khipuScatter`

De nivel superior (globales del script): `khipuScatter`

## Depende de

- [[engine.app_coordinator.js]] — usa `_toggle3D`
- [[engine.app_main.js]] — usa `LANG`
- [[nodes.nodes_seed.js]] — usa `NODE_META`

Se carga en [[app.html]] en la posición **97 de 97** (línea 3460), después de [[engine.app_canvas.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 97)
- [[engine.app_coordinator.js]] — usa `_khipuScatter`

## Pruebas que lo cubren

- [[tests.test_app_split.py]]
- [[tests.test_client_hardening.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (m) — app.html PARTIDO + 2 arreglos visibles — sw v268]]
- [[Sesión 2026-10-13 (l) — APP.HTML PARTIDO SIN CAMBIAR NADA (G5-06) — sw v267]]
