---
tipo: "api"
capa: "Chat y agentes"
rutas: 1
tags: ["capa/chat-agentes", "tipo/api"]
---

# API canvas

> 1 rutas · definidas en [[server.py]] · prefijo `/api/canvas`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `POST` | `/api/canvas/generate` | `canvas_generate` | [[server.py]] | [[engine.app_canvas.js]], [[engine.cockpit.js]], [[engine.command_center.js]], 1 prueba |
