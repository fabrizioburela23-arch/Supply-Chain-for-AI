---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-06"
ruta: "docs/ESTADO.md#L536"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-06 (iv) — JEV AL MANDO DEL CHAT (sw v248)

> Sesión de trabajo · `docs/ESTADO.md` línea 536 (12 líneas) · [[Índice de sesiones]]

## Resumen

Pedido de Fabrizio: "que Jev decida cuándo usar IA o responder desde la base local, y qué opción es mejor, para gastar lo mínimo en tokens". Antes Jev solo miraba (sombra). Ahora, con `DECIDE_CONTROL=chat_gate` (Railway), `core/decide.chat_plan` manda: dato puntual → ficha con datos en vivo SIN IA; consulta → ≤2 rondas; análisis → lo de siempre; @agente → local (sin IA) / rápido / profundo (`ask(mode=)`). Seguro:

## Archivos que menciona

- [[core.decide.py]]
- [[tests.test_jev_router.py]]

## Variables que menciona

[[ENV AI_PRICES_JSON]], [[ENV DECIDE_CONTROL]]

← más antigua: [[Sesión 2026-10-06 (iii) — HABILIDADES PROPIAS DE CADA AGENTE (sw v247)]] · más nueva: [[Sesión 2026-10-06 (v) — MARCA, TOOLS E INVOCAR (sw v249) + GEMINI 3.8 CON RESPALDOS]] →
