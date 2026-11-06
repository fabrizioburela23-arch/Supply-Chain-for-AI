---
tipo: "modulo"
capa: "Otros"
ruta: "scripts/eval_chat.py"
lenguaje: "python"
lineas: 121
aliases: ["scripts/eval_chat.py"]
tags: ["capa/otros", "tipo/modulo"]
---

# scripts/eval_chat.py

> Módulo · capa [[Capa Otros]] · 121 líneas · `scripts/eval_chat.py`

## Para qué sirve

Examen de oro del chat Khipu (stdlib, sin dependencias).

## API pública

- `grade(case, out, elapsed_s, max_s=…)` — Califica UNA respuesta → {ok, checks:{...}, fallas:[...]} (función pura: la prueban los tests). _(línea 32)_
- `ask(url, q, lang=…, timeout=…)` _(línea 60)_
- `report_md(results, url)` _(línea 79)_
- `main()` _(línea 90)_

## Depende de

_Nada interno._

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Endpoints que llama

- `POST /api/khipu/chat` → [[core.khipu_chat.py]] ([[API khipu]])

## Variables de entorno que lee (solo nombres)

- [[ENV KHIPU_URL]]

## Pruebas que lo cubren

- [[tests.test_eval_chat.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
