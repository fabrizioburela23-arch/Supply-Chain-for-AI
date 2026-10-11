---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-10"
ruta: "docs/ESTADO.md#L50"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-10 — NOCHE: IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)

> Sesión de trabajo · `docs/ESTADO.md` línea 50 (38 líneas) · [[Índice de sesiones]]

## Resumen

Fabrizio pagó Claude/Gemini/ElevenLabs (y Jev pronto). Workflow de 9 agentes (6 constructores + 2 revisores + corrector; 14 hallazgos: 11 arreglados por el corrector, 3 por mí). - IA (core/ai.py): orden POR NIVEL — `AI_ORDER_DEEP` (defecto claude,gemini,nvidia; IGNORA el AI_ORDER viejo) y `AI_ORDER_FAST` > `AI_ORDER` > defecto gemini,claude,nvidia (`provider_order`, `ai_route_state` → salud `routing`).

## Archivos que menciona

- [[app.html]]
- [[core.ai.py]]
- [[core.voice_agent.py]]
- [[engine.aispend.js]]
- [[engine.brief.js]]
- [[engine.clients.js]]
- [[engine.cockpit.js]]
- [[engine.explain.js]]
- [[engine.fincard.js]]
- [[engine.insights.js]]
- [[engine.loading.js]]
- [[engine.mcpconnect.js]]
- [[engine.portfolios.js]]
- [[engine.reconcile.js]]
- [[engine.research.js]]
- [[engine.riskreport.js]]
- [[engine.toast.js]]
- [[engine.voice.js]]
- [[engine.xray.js]]
- [[research.llm.py]]
- [[server.py]]

## Variables que menciona

[[ENV AI_MODEL_DEEP]], [[ENV AI_ORDER]], [[ENV AI_ORDER_DEEP]], [[ENV AI_ORDER_FAST]], [[ENV DECIDE_CONTROL]], [[ENV ELEVENLABS_ALLOW_OVERRIDE]], [[ENV TYPESAFE_API_KEY]]

← más antigua: [[Sesión 2026-10-09 — EL COMITÉ ENTRA A KHIPUS OS (sw v250)]] · más nueva: [[Sesión 2026-10-11 — BÓVEDA DE OBSIDIAN + MAPA DEL CÓDIGO]] →
