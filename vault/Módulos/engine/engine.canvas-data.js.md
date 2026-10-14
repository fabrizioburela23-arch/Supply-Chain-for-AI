---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "engine/canvas-data.js"
lenguaje: "javascript"
lineas: 72
aliases: ["engine/canvas-data.js"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# engine/canvas-data.js

> Módulo · capa [[Capa Chat y agentes]] · 72 líneas · `engine/canvas-data.js`

## Para qué sirve

Enriquecimiento de Canvas IA con datos en vivo (Khipu) Detecta empresas/tickers mencionados en una consulta y trae precios REALES de Finnhub (vía /api/quotes) para inyectarlos al contexto del Canvas, de modo que las tablas/gráficos comparativos usen datos de mercado reales, no estimados. Expone window.canvasEnrichData(query) → {tickers, live:{SYM:{price,change_pct}}}

## API pública (globales que define)

`window.canvasEnrichData`

## Depende de

- [[engine.app_main.js]] — usa `BASE`
- [[nodes.nodes_seed.js]] — usa `NODES`

Se carga en [[app.html]] en la posición **41 de 99** (línea 3098), después de [[engine.globe.js]] y antes de [[nodes.temporal_seed_facts.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 41)
- [[engine.app_canvas.js]] — usa `canvasEnrichData`
- [[engine.cockpit.js]] — usa `canvasEnrichData`
- [[engine.command_center.js]] — usa `canvasEnrichData`

## Endpoints que llama

- `GET /api/quotes` → [[server.py]] ([[API quotes]])

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
