---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/layers.js"
lenguaje: "javascript"
lineas: 132
aliases: ["engine/layers.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/layers.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 132 líneas · `engine/layers.js`

## Para qué sirve

SISTEMA DE CAPAS DEL MAPA (petición día 1 de Fabrizio) El mapa deja de ser "todo o nada": enciendes/apagas información como capas. Cada capa = un grupo de elementos SVG que ya existen (conexiones, etiquetas, anillos de riesgo, marcas, países). Alternar = una regla CSS (instantáneo, sin re-render). Botón "◱ Capas" arriba a la izquierda del mapa. La preferencia se recuerda en localStorage. KHIPUS OS (2026-10-11): botón y panel llevan .kos-themed → tokens --os-\* de engine/cockpit.js (claro = body sin .dark, oscuro = body.dark); el valor tras la coma de cada var() es el respaldo (la piel NEXUS vieja). Textos ES/EN y re-etiquetado al cambiar de idioma (regla bilingüe).

## API pública (globales que define)

_No define globales (código encapsulado)._

## Depende de

- [[engine.app_main.js]] — usa `LANG`

Se carga en [[app.html]] en la posición **72 de 101** (línea 3197), después de [[engine.livesim.js]] y antes de [[engine.brief.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 72)

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-22 al 24 — PHASE 1 Live Investment Graph COMPLETA + velocidad + 3D temporal]]
