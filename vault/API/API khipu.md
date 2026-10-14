---
tipo: "api"
capa: "Chat y agentes"
rutas: 3
tags: ["capa/chat-agentes", "tipo/api"]
---

# API khipu

> 3 rutas · definidas en [[core.khipu_chat.py]] · prefijo `/api/khipu`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `POST` | `/api/khipu/chat` | `chat_endpoint` | [[core.khipu_chat.py]] | [[core.ai_usage.py]], [[engine.khipu_chat.js]], 7 pruebas |
| `GET` | `/api/khipu/chat/progress/<req_id>` | `chat_progress_endpoint` | [[core.khipu_chat.py]] | [[engine.khipu_chat.js]], 3 pruebas |
| `GET` | `/api/khipu/tools` | `tools_endpoint` | [[core.khipu_chat.py]] | 1 prueba |
