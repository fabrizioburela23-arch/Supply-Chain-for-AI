---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "research/ask_agent.py"
lenguaje: "python"
lineas: 305
aliases: ["research/ask_agent.py"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# research/ask_agent.py

> Módulo · capa [[Capa Chat y agentes]] · 305 líneas · `research/ask_agent.py`

## Para qué sirve

PREGUNTARLE A UN ANALISTA dentro de la conversación.

## API pública

- `seat_from_words(txt)` _(línea 59)_
- `parse_mention(message)` — → (seat | 'all' | None, pregunta). seat None = no es una mención. _(línea 66)_
- `seat_meta(seat)` _(línea 83)_
- `seats_with_claims(session, entity_id)` _(línea 114)_
- `ask(session, seat, question, entity, lang=…, ai=…, skills=…, _pre=…, mode=…)` — Respuesta de UN puesto, CON SUS HABILIDADES (research/agent_skills): cada rol trae al instante SU paquete de datos en vivo (Cadena → tensor … _(línea 187)_
- `ask_all(session, question, entity, lang=…, ai=…, max_seats=…, mode=…)` — Todos los puestos con conclusiones (máx. max_seats) responden en paralelo. _(línea 267)_

**Internas** (empiezan con `_`): `_fold`, `_load_claims`, `_evidence`, `_package`, `_resolve`, `_strip_data`, `_fallback_text`

## Depende de

- [[core.ai.py]] — importa `_ai_complete`
- [[core.ai_usage.py]] — importa `bind`
- [[research.agent_skills.py]] — importa `agent_skills`
- [[research.committee.py]] — importa `_evidence_rows`, `_resolve_entity`
- [[research.deliberation.py]] — importa `SEAT_ORDER`, `seat_name`
- [[research.models.py]] — importa `ResearchClaim`

## Lo usan

- [[core.khipu_chat.py]] — lo importa
- [[research.committee_api.py]] — lo importa

_Además lo importan 3 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_ask_agent.py]]
- [[tests.test_jev_router.py]]
- [[tests.test_khipus_os_server.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (iii) — HABILIDADES PROPIAS DE CADA AGENTE (sw v247)]]
- [[Sesión 2026-10-05 (j) — COMANDOS Y AGENTES EN EL CHAT (sw v212)]]
- [[Sesión 2026-10-04 (g) — KHIPU COMO ASISTENTE - ANALISTAS EN EL CHAT, PROMPT, MEMORIA]]
