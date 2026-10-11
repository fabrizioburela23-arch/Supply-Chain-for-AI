---
tipo: "variable"
capa: "Infraestructura"
nombre: "GEMINI_KEY"
documentada: true
tags: ["capa/infraestructura", "tipo/variable"]
---

# GEMINI_KEY

> Variable de entorno · se configura en Railway (Variables). Aquí solo el **nombre**, nunca el valor.

## La leen

- [[core.config.py]]
- [[core.http.py]] _(en una lista de nombres, p. ej. para tapar secretos en logs)_

## Pruebas que la fijan o nombran

- [[tests.test_ai_gemini_fast.py]]
- [[tests.test_ai_json.py]]
- [[tests.test_infra.py]]
- [[tests.test_overnight3_diag_bilingual.py]]
- [[tests.test_repair_research.py]]
- [[tests.test_security.py]]

## ¿Está documentada en CLAUDE.md?

Sí — en la lista **Variables de entorno** de [[Doc CLAUDE]].

## Mencionada en sesiones

- [[Sesión 2026-10-04 (f) — EXPECTING VALUE EN INVESTIGAR - JSON ESTRICTO + MENSAJES PARA]]
