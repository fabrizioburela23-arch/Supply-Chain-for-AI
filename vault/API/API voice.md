---
tipo: "api"
capa: "Voz"
rutas: 8
tags: ["capa/voz", "tipo/api"]
---

# API voice

> 8 rutas · definidas en [[core.voice_api.py]] · prefijo `/api/voice`

Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.

| Método | Ruta | Función | Módulo | Lo llaman |
|---|---|---|---|---|
| `POST` | `/api/voice/adopt` | `voice_adopt` | [[core.voice_api.py]] | 2 pruebas |
| `GET` | `/api/voice/agent-diag` | `voice_agent_diag` | [[core.voice_api.py]] | 3 pruebas |
| `POST` | `/api/voice/agent-tune` | `voice_agent_tune` | [[core.voice_api.py]] | 3 pruebas |
| `GET` | `/api/voice/bixby-prompt` | `bixby_system_prompt` | [[core.voice_api.py]] | [[engine.voice.js]], 5 pruebas |
| `POST` | `/api/voice/session` | `voice_session` | [[core.voice_api.py]] | [[engine.voice.js]], 4 pruebas |
| `GET,POST` | `/api/voice/sync-agent` | `voice_sync_agent` | [[core.voice_api.py]] | 3 pruebas |
| `GET` | `/api/voice/tour/<lang>/<int:step>` | `voice_tour_audio` | [[core.voice_api.py]] | [[engine.cockpit.js]], 4 pruebas |
| `GET` | `/api/voice/voices` | `voice_voices` | [[core.voice_api.py]] | 2 pruebas |
