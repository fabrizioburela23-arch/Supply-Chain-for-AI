---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "engine/command_center.js"
lenguaje: "javascript"
lineas: 433
aliases: ["engine/command_center.js"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# engine/command_center.js

> Módulo · capa [[Capa Chat y agentes]] · 433 líneas · `engine/command_center.js`

## Para qué sirve

Khipu Command Center (Khipu Finance) UN SOLO Khipu: el botón original del header lo abre. NO hay orbe flotante. El panel (input + feed de resultados) aparece como dropdown arriba-derecha, en su espacio dedicado, sin tapar el contenido de abajo. Escribe O habla; Khipu ejecuta y muestra la respuesta inline. Reutiliza: switchTab, jumpTo, activateStress, nexusCore.runPreset, _openSecondBrain, canvasGenerate (_cvRenderCard) y BixbyVoice (voz). Endpoint: /api/khipu/chat (cerebro con herramientas, engine/khipu_chat.js). Expone window.BixbyCC.

## API pública (globales que define)

`window.BixbyCC`

## Depende de

- [[engine.app_canvas.js]] — usa `_cvRenderCard`, `canvasGenerate`
- [[engine.app_coordinator.js]] — usa `_openSecondBrain`, `nexusCore`
- [[engine.app_main.js]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `activateStress`, `computeNRS`, `jumpTo`, `switchTab`
- [[engine.canvas-data.js]] — usa `canvasEnrichData`
- [[engine.cockpit.js]] — usa `BixbyCockpit`, `_openBrokerConfirm`, `_parseTradeCommand`
- [[engine.compare.js]] — usa `openCompare`
- [[engine.khipu_chat.js]] — usa `KhipuChat`
- [[engine.khipu_lang.js]] — usa `KHIPU`
- [[engine.livesim.js]] — usa `_lsToggle`
- [[engine.pickers.js]] — usa `KhipuPick`
- [[engine.resolve.js]] — usa `KhipuResolve`, `_surface`
- [[engine.temporal-graph.js]] — usa `__tkgOpenObj`
- [[engine.voice.js]] — usa `BixbyVoice`
- [[engine.xray.js]] — usa `openXRay`
- [[nodes.nodes_seed.js]] — usa `NODES`

Se carga en [[app.html]] en la posición **97 de 104** (línea 3251), después de [[engine.live.js]] y antes de [[sim.scenario_builder.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 97)
- [[app.html]] — usa `BixbyCC`

## Endpoints que llama

- `POST /api/canvas/generate` → [[server.py]] ([[API canvas]])

## Pruebas que lo cubren

_Ninguna prueba lo importa ni menciona su ruta._
