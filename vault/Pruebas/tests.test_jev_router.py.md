---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_jev_router.py"
lenguaje: "python"
lineas: 161
aliases: ["tests/test_jev_router.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_jev_router.py

> Prueba · capa [[Capa Pruebas]] · 161 líneas · `tests/test_jev_router.py`

## Qué prueba

Jev AL MANDO del chat (core/decide.chat_plan + core/khipu_chat): elige el camino más barato que alcanza. local_fact → ficha con datos en vivo SIN IA · needs_tools → pocas consultas · deep → lo de siempre · @agente → nivel del analista (local / rápido / profundo). Sin control o sin confianza → nada cambia.

**7** funciones `test_…`.

## Cubre

- [[core.ai.py]]
- [[core.decide.py]]
- [[core.khipu_chat.py]]
- [[core.live_facts.py]]
- [[mcp_server.tools.py]]
- [[ontology.db.py]]
- [[research.agent_skills.py]]
- [[research.ask_agent.py]]

## Variables de entorno que fija o nombra

[[ENV DECIDE_CONTROL]], [[ENV TYPESAFE_API_KEY]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-06 (iv) — JEV AL MANDO DEL CHAT (sw v248)]]
