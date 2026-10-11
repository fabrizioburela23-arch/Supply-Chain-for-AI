---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/layers.js"
lenguaje: "javascript"
lineas: 101
aliases: ["engine/layers.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/layers.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 101 líneas · `engine/layers.js`

## Para qué sirve

SISTEMA DE CAPAS DEL MAPA (petición día 1 de Fabrizio) El mapa deja de ser "todo o nada": enciendes/apagas información como capas. Cada capa = un grupo de elementos SVG que ya existen (conexiones, etiquetas, anillos de riesgo, marcas, países). Alternar = una regla CSS (instantáneo, sin re-render). Piel NEXUS. Botón "◱ Capas" arriba a la izquierda del mapa. La preferencia se recuerda en localStorage.

## API pública (globales que define)

`window._layersApply`

## Depende de

_Nada interno._

Se carga en [[app.html]] en la posición **68 de 93** (línea 7907), después de [[engine.livesim.js]] y antes de [[engine.brief.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 68)

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-22 al 24 — PHASE 1 Live Investment Graph COMPLETA + velocidad + 3D temporal]]
