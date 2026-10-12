---
tipo: "modulo"
capa: "Voz"
ruta: "core/voice_agent.py"
lenguaje: "python"
lineas: 1042
aliases: ["core/voice_agent.py"]
tags: ["capa/voz", "tipo/modulo"]
---

# core/voice_agent.py

> Módulo · capa [[Capa Voz]] · 1.042 líneas · `core/voice_agent.py`

## Para qué sirve

Khipu (voz) ↔ ElevenLabs Agents Platform (oct-2026).

## API pública

- `llm_is_legacy(llm)` _(línea 69)_
- `llm_target()` _(línea 76)_
- `tts_model_unknown(model)` — ¿Un modelo que no conocemos (p. ej. uno NUEVO de ElevenLabs que el dueño eligió)? Se deja como está. _(línea 85)_
- `tts_fix_for(model, language=…)` — Modelo TTS al que hay que pasar (o None si el actual sirve). Solo se cambian los deprecados, los viejos conocidos, los de solo inglés en un … _(línea 91)_
- `override_env_on()` _(línea 109)_
- `classify_error(status_code, body=…, exc=…)` _(línea 132)_
- `describe(err, what=…)` — Mensaje bilingüe y arreglo concreto (clics) para un error clasificado. `what`: 'key' (la clave) · 'agent' (el agente) · 'session' … _(línea 190)_
- `get_agent(key, agent_id, http, cached=…, timeout=…, max_age=…)` — → (cfg | None, err | None). Caché 10 min (la usa /api/voice/session); `max_age` (s) pide una lectura más fresca (el audio del recorrido: si … _(línea 294)_
- `forget_agent(agent_id=…)` _(línea 316)_
- `agent_summary(cfg)` — Lo relevante del agente, con nombres planos. _(línea 328)_
- `session_hints(cfg)` — Lo que el navegador necesita para NO mandar overrides prohibidos. _(línea 360)_
- `get_signed_url(key, agent_id, http, timeout=…)` _(línea 372)_
- `list_voices(key, http, timeout=…)` — Voces de la cuenta (máx 60) + las mejor valoradas EN ESPAÑOL de la biblioteca compartida (12). Nunca lanza: los fallos quedan en … _(línea 400)_
- `adopt_shared_voice(key, public_owner_id, voice_id, name, http, timeout=…)` — Copia una voz de la biblioteca compartida a la cuenta (paso previo a asignarla al agente). Los ids van EN la URL: quien llama ya los validó … _(línea 433)_
- `tour_tts_models(agent_model, language=…)` — Modelos a probar para el audio del recorrido: primero el del agente (misma voz y estilo; con su nombre del API de texto a voz si es uno de … _(línea 457)_
- `tour_voice(cfg, language=…)` — La voz que el agente USA en una conversación en `language` (2026-10-12: el botón del recorrido sonaba a la "voz vieja"): la de la variante … _(línea 474)_
- `synthesize(key, voice_id, text, http, models=…, output_format=…, timeout=…, voice_settings=…)` — Texto → audio MP3 con la voz `voice_id` (POST /v1/text-to-speech/{voice_id}). Prueba los modelos en orden y solo pasa al siguiente si … _(línea 495)_
- `list_tools(key, http, max_pages=…, timeout=…)` — → ({tool_id: tool_config}, err|None). Todas las del workspace (paginado). _(línea 528)_
- `tool_payload(spec)` — Spec interna (la de server._bixby_client_tools) → tool_config de la API. _(línea 566)_
- `ensure_tools(key, http, specs, current_ids, timeout=…, retired_names=…)` — Crea/actualiza las herramientas cliente de Khipu y devuelve sus ids. Reusa (por nombre) las que el agente ya referencia — incluidas las que … _(línea 580)_
- `build_agent_patch(cur_summary, prompt, tool_ids, language=…, allow_overrides=…, legacy_tools=…)` — → (payload PATCH, cambios{tts_fixed, llm_fixed, client_events_fixed, overrides_enabled}). _(línea 648)_
- `sync_agent(key, agent_id, prompt, tool_specs, http, language=…, allow_overrides=…, retired_names=…)` — Empuja el cerebro de Khipu al agente: prompt + herramientas (recursos con tool_ids) + idioma, y REPARA lo viejo: TTS deprecado o … _(línea 684)_
- `diagnose(key, agent_id, http, expected_tools=…, prompt=…, full=…, retired_tools=…)` — Revisa clave, saldo, agente, LLM, voz, modelo TTS, overrides, herramientas, eventos y prompt. → {configured, ok, checks[], fixes[], detail … _(línea 776)_

**Internas** (empiezan con `_`): `_hdr`, `_json`, `_http_err`, `_exc_err`, `_sleep`, `_cc`, `_subset_equal`, `_check`, `_finish`

## Depende de

_Nada interno._

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 5 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV ELEVENLABS_ALLOW_OVERRIDE]]
- [[ENV ELEVENLABS_LLM]]

## Pruebas que lo cubren

- [[tests.test_cleanup_server.py]]
- [[tests.test_overnight3_diag_bilingual.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_overnight_voice_server.py]]
- [[tests.test_voice_tour.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
