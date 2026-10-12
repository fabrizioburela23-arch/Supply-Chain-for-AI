---
tipo: "api"
capa: "Voz"
rutas: 8
tags: ["capa/voz", "tipo/api"]
---

# API voice

> 8 rutas · definidas en [[server.py]] · prefijo `/api/voice`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `POST` | `/api/voice/adopt` | `voice_adopt` | [[server.py]] | 1 prueba |
| `GET` | `/api/voice/agent-diag` | `voice_agent_diag` | [[server.py]] | 2 pruebas |
| `POST` | `/api/voice/agent-tune` | `voice_agent_tune` | [[server.py]] | 2 pruebas |
| `GET` | `/api/voice/bixby-prompt` | `bixby_system_prompt` | [[server.py]] | [[engine.voice.js]], 3 pruebas |
| `POST` | `/api/voice/session` | `voice_session` | [[server.py]] | [[engine.voice.js]], 2 pruebas |
| `GET,POST` | `/api/voice/sync-agent` | `voice_sync_agent` | [[server.py]] | 2 pruebas |
| `GET` | `/api/voice/tour/<lang>/<int:step>` | `voice_tour_audio` | [[server.py]] | [[engine.cockpit.js]], 2 pruebas |
| `GET` | `/api/voice/voices` | `voice_voices` | [[server.py]] | 1 prueba |
