---
tipo: "modulo"
capa: "Voz"
ruta: "core/voice_api.py"
lenguaje: "python"
lineas: 825
aliases: ["core/voice_api.py"]
tags: ["capa/voz", "tipo/modulo"]
---

# core/voice_api.py

> Módulo · capa [[Capa Voz]] · 825 líneas · `core/voice_api.py`

## Para qué sirve

Voz de Khipu — rutas /api/voice/\* (G5-05, lote I4: salieron de server.py SIN cambiar comportamiento).

## API pública

- `bind(host)` — server.py se pasa a sí mismo: la config de ElevenLabs y _diag_redact se leen de ahí en cada llamada. _(línea 30)_
- `voice_agent_diag()` — Diagnóstico ACCIONABLE de la voz: clave, saldo/plan, agente, LLM, voz, modelo TTS, eventos, herramientas, prompt y overrides — con la lista … _(línea 43)_
- `voice_voices()` — Voces disponibles: las de la cuenta + las mejor valoradas EN ESPAÑOL de la biblioteca compartida de ElevenLabs (para arreglar la 'voz … _(línea 74)_
- `voice_adopt()` — Adopta una voz de la biblioteca compartida a la cuenta (paso previo a asignarla al agente). Mismo candado que agent-tune + PIN de operador. … _(línea 178)_
- `voice_agent_tune()` — Ajuste FINO del agente (modelo TTS / idioma / voice_id). Requiere ELEVENLABS_ALLOW_OVERRIDE=1 (mismo candado que adopt) + PIN de operador. … _(línea 215)_
- `voice_sync_agent()` — Sincroniza el agente de ElevenLabs con el cerebro definido aquí (PATCH del agente). PIN de operador: antes cualquiera podía dispararlo en … _(línea 648)_
- `start_autosync()` — Auto-sync al arrancar (BIXBY_AUTOSYNC=0 para desactivar). En background para no retrasar el boot; idempotente aunque los 2 workers de … _(línea 678)_
- `bixby_system_prompt()` — Returns Khipu's system prompt for ElevenLabs agent configuration. _(línea 693)_
- `voice_session()` — URL firmada (un solo uso, la clave NUNCA sale del server) + qué overrides permite el agente, para que el navegador no mande uno prohibido … _(línea 713)_
- `voice_tour_audio(lang, step)` — Audio MP3 de la frase `step` del recorrido guiado, con la voz del agente de Khipu. 404 sin voz configurada o paso inexistente (el navegador … _(línea 767)_

**Internas** (empiezan con `_`): `_voice_override_off`, `_ledger_503`, `_voice_decision`, `_voice_outcome`, `_agent_before`, `_bixby_client_tools`, `_sync_bixby_agent`, `_voice_autosync_log`

## Depende de

- [[core.agents_registry.py]] — importa `AGENTS`, `AGENT_NAMES`
- [[core.decision_sites.py]] — importa `decision_sites`
- [[core.decisions.py]] — importa `decisions`
- [[core.http.py]] — importa `rate_limit`
- [[core.pin.py]] — importa `require_operator`
- [[core.tour.py]] — importa `tour`
- [[core.voice_agent.py]] — importa `adopt_shared_voice`, `list_voices`, `override_env_on`, `voice_agent`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `POST` | `/api/voice/adopt` | `voice_adopt` | 2 pruebas |
| `GET` | `/api/voice/agent-diag` | `voice_agent_diag` | 3 pruebas |
| `POST` | `/api/voice/agent-tune` | `voice_agent_tune` | 3 pruebas |
| `GET` | `/api/voice/bixby-prompt` | `bixby_system_prompt` | [[engine.voice.js]], 5 pruebas |
| `POST` | `/api/voice/session` | `voice_session` | [[engine.voice.js]], 4 pruebas |
| `GET,POST` | `/api/voice/sync-agent` | `voice_sync_agent` | 3 pruebas |
| `GET` | `/api/voice/tour/<lang>/<int:step>` | `voice_tour_audio` | [[engine.cockpit.js]], 4 pruebas |
| `GET` | `/api/voice/voices` | `voice_voices` | 2 pruebas |

Grupos: [[API voice]]

## Variables de entorno que lee (solo nombres)

- [[ENV BIXBY_AUTOSYNC]]

## Pruebas que lo cubren

- [[tests.test_cleanup_server.py]]
- [[tests.test_overnight3_mic_voice_state.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_overnight_voice_server.py]]
- [[tests.test_security.py]]
- [[tests.test_server_smoke.py]]
- [[tests.test_voice_agent_split.py]]
- [[tests.test_voice_tour.py]]
- [[tests.test_voice_tour_client.py]]
- [[tests.test_voice_tour_drive.py]]
- [[tests.test_voice_tour_narrator.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (k) — FASE 2+ LOTE I - rutas con decisión, CSP estricta, riesgo]]
