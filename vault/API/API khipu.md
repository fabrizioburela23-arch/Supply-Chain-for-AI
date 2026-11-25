---
tipo: "api"
capa: "Chat y agentes"
rutas: 4
tags: ["capa/chat-agentes", "tipo/api"]
---

# API khipu

> 4 rutas · definidas en [[core.khipu_chat.py]] · prefijo `/api/khipu`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `GET` | `/api/khipu/a2ui/catalog.json` | `a2ui_catalog_endpoint` | [[core.khipu_chat.py]] | 1 prueba |
| `POST` | `/api/khipu/chat` | `chat_endpoint` | [[core.khipu_chat.py]] | [[core.ai_usage.py]], [[engine.khipu_chat.js]], [[scripts.eval_chat.py]], 7 pruebas |
| `GET` | `/api/khipu/chat/progress/<req_id>` | `chat_progress_endpoint` | [[core.khipu_chat.py]] | [[engine.khipu_chat.js]], 3 pruebas |
| `GET` | `/api/khipu/tools` | `tools_endpoint` | [[core.khipu_chat.py]] | 1 prueba |
