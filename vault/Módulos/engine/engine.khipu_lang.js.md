---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "engine/khipu_lang.js"
lenguaje: "javascript"
lineas: 376
aliases: ["engine/khipu_lang.js"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# engine/khipu_lang.js

> Módulo · capa [[Capa Chat y agentes]] · 376 líneas · `engine/khipu_lang.js`

## Para qué sirve

Fase 4 del roadmap de ontología: lenguaje de comandos KHIPU, corto y componible: &lt;ENTIDAD> &lt;FUNCIÓN> [ARGS]. Se intenta ANTES de mandar el texto a la IA (Khipu): si no calza con esta gramática, devuelve null y Khipu sigue su camino normal (lenguaje natural, sin round-trip a Claude — más rápido para comandos exactos). Cada función es un atajo a la MISMA API que usan los paneles — cero lógica duplicada.

## API pública (globales que define)

`window.KHIPU`

## Depende de

- [[app.html]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `_tradeErrText`, `_tradeFetch`, `switchTab`
- [[engine.clients.js]] — usa `KhipuClients`
- [[engine.committee.js]] — usa `KhipuCommittee`
- [[engine.maptime.js]] — usa `KhipuMapTime`
- [[engine.mcpconnect.js]] — usa `KhipuMCP`
- [[engine.research.js]] — usa `KhipuResearch`
- [[engine.resolve.js]] — usa `KhipuResolve`
- [[engine.riskreport.js]] — usa `KhipuRisk`
- [[engine.temporal-graph.js]] — usa `__tkgSetDate`
- [[engine.toast.js]] — usa `khipuActor`

Se carga en [[app.html]] en la posición **47 de 92** (línea 7840), después de [[engine.maptime.js]] y antes de [[engine.guide.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 47)
- [[engine.cockpit.js]] — usa `KHIPU`
- [[engine.command_center.js]] — usa `KHIPU`

## Endpoints que llama

- `GET /api/fundamentals/<ticker>` → [[server.py]] ([[API fundamentals]])
- `GET /api/matrix/<rel_type>` → [[matrix.api.py]] ([[API matrix]])
- `GET /api/matrix/factors` → [[matrix.api.py]] ([[API matrix]])
- `GET /api/ontology/alerts` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/feed` → [[ontology.api.py]] ([[API ontology]])
- `GET /api/ontology/graph/diff` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/matrix/factor/fire` → [[matrix.api.py]] ([[API matrix]])
- `POST /api/ontology/actions/<action_type>` → [[ontology.api.py]] ([[API ontology]])
- `POST /api/ontology/alerts` → [[ontology.api.py]] ([[API ontology]])

## Pruebas que lo cubren

- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_khipu_chat.py]]
