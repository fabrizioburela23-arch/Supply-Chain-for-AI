---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-04"
ruta: "docs/ESTADO.md#L899"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-04 (f) — "EXPECTING VALUE" EN INVESTIGAR: JSON ESTRICTO + MENSAJES PARA PERSONAS

> Sesión de trabajo · `docs/ESTADO.md` línea 899 (13 líneas) · [[Índice de sesiones]]

## Resumen

Fabrizio tiene saldo en Gemini pero Investigar daba "IA falló · Expecting value: line 1 column 1": un proveedor SÍ respondió, pero sin JSON (Gemini 2.5 flash "pensando" se come los tokens y corta, o contesta en prosa). `core.ai._ai_json(system, prompt, …)`: _ai_complete + _extract_json y, si no hay JSON y existe GEMINI_KEY, UN reintento con `_complete_gemini(json_mode=True)` (JSON estricto,

## Archivos que menciona

- [[core.ai.py]]
- [[tests.test_ai_json.py]]

## Variables que menciona

[[ENV GEMINI_KEY]]

← más antigua: [[Sesión 2026-10-04 (e) — INICIO DE LA CABINA REDISEÑADO + FEED SIN NOTICIAS VIEJAS]] · más nueva: [[Sesión 2026-10-04 (g) — KHIPU COMO ASISTENTE - ANALISTAS EN EL CHAT, PROMPT, MEMORIA]] →
