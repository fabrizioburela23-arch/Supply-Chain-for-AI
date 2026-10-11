---
tipo: "modulo"
capa: "Investigación"
ruta: "research/errors.py"
lenguaje: "python"
lineas: 75
aliases: ["research/errors.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/errors.py

> Módulo · capa [[Capa Investigación]] · 75 líneas · `research/errors.py`

## Para qué sirve

traduce errores técnicos de la IA a lenguaje simple.

## API pública

- `friendly(err)` — (es, en) o (None, None) si no se reconoce. _(línea 58)_
- `run_hint(errors)` _(línea 69)_

## Depende de

_Nada interno._

## Lo usan

- [[core.khipu_chat.py]] — lo importa
- [[research.api.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.runner.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_analytics.py]]
- [[tests.test_committee_os_narr.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-04 (g) — KHIPU COMO ASISTENTE - ANALISTAS EN EL CHAT, PROMPT, MEMORIA]]
- [[Sesión 2026-10-02 (noche) — ANÁLISIS MÁS PROFUNDO + CONCLUSIONES EN TODAS PARTES (sw v179)]]
