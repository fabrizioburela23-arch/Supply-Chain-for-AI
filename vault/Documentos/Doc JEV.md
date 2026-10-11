---
tipo: "documento"
capa: "Documentación"
ruta: "docs/JEV.md"
lenguaje: "markdown"
lineas: 61
aliases: ["docs/JEV.md"]
tags: ["capa/documentacion", "tipo/documento"]
---

# docs/JEV.md

> Documento · capa [[Capa Documentación]] · 61 líneas · `docs/JEV.md`

## De qué trata

Jev (TypeSafe AI) en Khipus — modelo de DECISIÓN (manda en el chat por defecto; además en sombra) — Jev no escribe: recibe un \*\*estado\*\* + \*\*preguntas tipadas\*\* y devuelve respuestas que el código usa directo, con probabilidades calibradas y confianza. `choice` (elige una opción) · `score` (nivel en una rúbrica) · `noul` (¿es verdad?, 0-1). Muchas preguntas por llamada se evalúan en paralelo → se piden todas las que el código pueda necesitar y se combinan en código (speculative fan-out).

## Menciona

- [[core.ai_usage.py]]
- [[core.decide.py]]
- [[core.decide_api.py]]
- [[core.khipu_chat.py]]
- [[research.models.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-04 (c) — JEV (TYPESAFE) EN MODO SOMBRA - PORTERO DEL CHAT (sw v188)]]
