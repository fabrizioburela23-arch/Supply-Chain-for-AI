---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "core/decide.py"
lenguaje: "python"
lineas: 356
aliases: ["core/decide.py"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# core/decide.py

> Módulo · capa [[Capa Chat y agentes]] · 356 líneas · `core/decide.py`

## Para qué sirve

JEV (TypeSafe AI, modelo "System One"): DECISIONES, no texto.

## API pública

- `available()` _(línea 83)_
- `shadow_mode()` _(línea 87)_
- `control_features()` — Funciones donde Jev MANDA (2026-10-10, Fabrizio pagó TypeSafe): · DECIDE_CONTROL sin poner (o vacía) → ('chat_gate',): Jev decide la ruta … _(línea 95)_
- `control(feature)` — ¿Jev MANDA en esta función? Hace falta clave (available) y que la función esté en control_features(). _(línea 109)_
- `ask(state, questions, feature=…, timeout=…)` — Una llamada a Jev. Devuelve {id: answer} o None (sin clave/red/error). Las preguntas van tal cual el formato de TypeSafe … _(línea 129)_
- `shadow(feature, key, decision, actual, agree)` _(línea 174)_
- `shadow_report(days=…, limit=…)` — Acuerdo Jev ↔ sistema por función (Postgres si hay; si no, memoria). _(línea 199)_
- `chat_gate_start(message, lang=…)` — Lanza la decisión de Jev en paralelo (no frena el chat). None si no aplica. _(línea 262)_
- `chat_gate_finish(fut, out, message=…)` — Compara la decisión de Jev con lo que hizo el chat y lo deja en sombra. _(línea 281)_
- `decision_of(ans)` — Respuesta cruda de Jev → decisión plana. La confianza de la ruta: `confidence` o, si no viene, la probabilidad de la opción elegida. _(línea 314)_
- `chat_plan(fut, wait_s=…)` — Jev AL MANDO del chat: → decisión {route, confidence, …} que el chat OBEDECE, o None (sin control, sin respuesta a tiempo o confianza < … _(línea 330)_

**Internas** (empiezan con `_`): `_key`, `_now`, `_trim_state`, `_persist`, `_actual_route`, `_finish_bg`, `_num`, `_compare`

## Depende de

- [[core.ai_usage.py]] — importa `ai_usage`
- [[core.governance.py]] — importa `governance`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[research.models.py]] — importa `DecisionShadow`

## Lo usan

- [[core.decide_api.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa

_Además lo importan 5 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV DECIDE_CONTROL]]
- [[ENV DECIDE_ENABLED]]
- [[ENV DECIDE_SHADOW]]
- [[ENV DECIDE_TIMEOUT_S]]
- [[ENV TYPESAFE_API_KEY]]
- [[ENV TYPESAFE_API_URL]]
- [[ENV TYPESAFE_KEY]]
- [[ENV TYPESAFE_MODEL]]

## Pruebas que lo cubren

- [[tests.test_decide.py]]
- [[tests.test_governance_seed_parity.py]]
- [[tests.test_jev_router.py]]
- [[tests.test_overnight_ai_routing.py]]
- [[tests.test_overnight_fixes_review.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]]
- [[Sesión 2026-10-06 (iv) — JEV AL MANDO DEL CHAT (sw v248)]]
- [[Sesión 2026-10-04 (c) — JEV (TYPESAFE) EN MODO SOMBRA - PORTERO DEL CHAT (sw v188)]]
