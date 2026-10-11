---
tipo: "datos"
capa: "Datos del catálogo"
ruta: "nodes/private_valuations.js"
lenguaje: "javascript"
lineas: 823
aliases: ["nodes/private_valuations.js"]
tags: ["capa/datos-catalogo", "tipo/datos"]
---

# nodes/private_valuations.js

> Datos · capa [[Capa Datos del catálogo]] · 823 líneas · `nodes/private_valuations.js`

## Para qué sirve

GENERADO por scripts/build_private_valuations.py. Última valuación CERRADA verificada con fuente de empresas privadas (y la negociación, aparte). Lo "en vivo" lo agrega el Dossier desde los titulares (/api/company/valuation). No editar a mano: regenerar con una verificación nueva.

## Qué datos contiene

- ~64 entradas con clave
- 40 KB

_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._

## API pública (globales que define)

`window.PRIVATE_VALUATIONS`

## Depende de

- [[nodes.preipo_intel.js]] — usa `PREIPO_INTEL`

Se carga en [[app.html]] en la posición **15 de 91** (línea 1450), después de [[nodes.listing_status.js]] y antes de [[nodes.links_all.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 15)
- [[app.html]] — usa `PRIVATE_VALUATIONS`
- [[engine.fincard.js]] — usa `PRIVATE_VALUATIONS`
- [[sim.scenario_builder.js]] — usa `PRIVATE_VALUATIONS`
- [[mcp_server.tools.py]] — lo nombra por su ruta
- [[scripts.build_private_valuations.py]] — lo nombra por su ruta
- [[scripts.export_graph_v0.js]] — lo nombra por su ruta

## Pruebas que lo cubren

- [[tests.test_verified_valuations.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (x) — CIFRAS VIEJAS - VERIFICADAS - EN VIVO (sw v231)]]
- [[Sesión 2026-09-28 (d) — Valuación de PRIVADAS en vivo (sw v152)]]
