---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "core/decide.py"
lenguaje: "python"
lineas: 349
aliases: ["core/decide.py"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# core/decide.py

> Módulo · capa [[Capa Chat y agentes]] · 349 líneas · `core/decide.py`

## Para qué sirve

JEV (TypeSafe AI, modelo "System One"): DECISIONES, no texto.

## API pública

- `available()` _(línea 76)_
- `shadow_mode()` _(línea 80)_
- `control_features()` — Funciones donde Jev MANDA (2026-10-10, Fabrizio pagó TypeSafe): · DECIDE_CONTROL sin poner (o vacía) → ('chat_gate',): Jev decide la ruta … _(línea 88)_
- `control(feature)` — ¿Jev MANDA en esta función? Hace falta clave (available) y que la función esté en control_features(). _(línea 102)_
- `ask(state, questions, feature=…, timeout=…)` — Una llamada a Jev. Devuelve {id: answer} o None (sin clave/red/error). Las preguntas van tal cual el formato de TypeSafe … _(línea 122)_
- `shadow(feature, key, decision, actual, agree)` _(línea 167)_
- `shadow_report(days=…, limit=…)` — Acuerdo Jev ↔ sistema por función (Postgres si hay; si no, memoria). _(línea 192)_
- `chat_gate_start(message, lang=…)` — Lanza la decisión de Jev en paralelo (no frena el chat). None si no aplica. _(línea 255)_
- `chat_gate_finish(fut, out, message=…)` — Compara la decisión de Jev con lo que hizo el chat y lo deja en sombra. _(línea 274)_
- `decision_of(ans)` — Respuesta cruda de Jev → decisión plana. La confianza de la ruta: `confidence` o, si no viene, la probabilidad de la opción elegida. _(línea 307)_
- `chat_plan(fut, wait_s=…)` — Jev AL MANDO del chat: → decisión {route, confidence, …} que el chat OBEDECE, o None (sin control, sin respuesta a tiempo o confianza < … _(línea 323)_

**Internas** (empiezan con `_`): `_key`, `_now`, `_trim_state`, `_persist`, `_actual_route`, `_finish_bg`, `_num`, `_compare`

## Depende de

- [[core.ai_usage.py]] — importa `ai_usage`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[research.models.py]] — importa `DecisionShadow`

## Lo usan

- [[core.decide_api.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa

_Además lo importan 4 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV DECIDE_CONTROL]]
- [[ENV DECIDE_ENABLED]]
- [[ENV DECIDE_MIN_CONF]]
- [[ENV DECIDE_SHADOW]]
- [[ENV DECIDE_TIMEOUT_S]]
- [[ENV DECIDE_WAIT_S]]
- [[ENV TYPESAFE_API_KEY]]
- [[ENV TYPESAFE_API_URL]]
- [[ENV TYPESAFE_KEY]]
- [[ENV TYPESAFE_MODEL]]

## Pruebas que lo cubren

- [[tests.test_decide.py]]
- [[tests.test_jev_router.py]]
- [[tests.test_overnight_ai_routing.py]]
- [[tests.test_overnight_fixes_review.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
- [[Sesión 2026-10-06 (iv) — JEV AL MANDO DEL CHAT (sw v248)]]
- [[Sesión 2026-10-04 (c) — JEV (TYPESAFE) EN MODO SOMBRA - PORTERO DEL CHAT (sw v188)]]
