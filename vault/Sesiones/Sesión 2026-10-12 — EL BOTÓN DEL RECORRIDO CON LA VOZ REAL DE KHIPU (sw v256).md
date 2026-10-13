---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-12"
ruta: "docs/ESTADO.md#L140"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-12 — EL BOTÓN DEL RECORRIDO CON LA VOZ REAL DE KHIPU (sw v256)

> Sesión de trabajo · `docs/ESTADO.md` línea 140 (18 líneas) · [[Índice de sesiones]]

## Resumen

Fabrizio: "Cuando aprieto «Ver el recorrido en un minuto», usa la voz antigua. Solo cuando se lo pido por voz, usa la voz nueva." Causas: (1) el botón SIEMPRE tocaba los clips del servidor — `isConfigured()` buscaba un `Keys` global que en la app real no existe (está en `V8.Keys`); (2) los clips usaban solo la voz principal, sin los ajustes del agente, con el nombre de modelo de conversación, y quedaban guardados 1 h en el navegador / 10 min en el servidor.

## Archivos que menciona

- [[tests.test_voice_tour_narrator.py]]

← más antigua: [[Sesión 2026-10-11 (c) — LA VOZ DE KHIPU PARA KHIPUS OS + RECORRIDO DE UN MINUTO CON SU]] · más nueva: [[Sesión 2026-10-12 (b) — EL RECORRIDO DE VOZ YA NO SE QUEDA EN EL PASO 1 (sw v257)]] →
