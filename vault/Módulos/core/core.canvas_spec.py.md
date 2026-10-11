---
tipo: "modulo"
capa: "Chat y agentes"
ruta: "core/canvas_spec.py"
lenguaje: "python"
lineas: 366
aliases: ["core/canvas_spec.py"]
tags: ["capa/chat-agentes", "tipo/modulo"]
---

# core/canvas_spec.py

> Módulo · capa [[Capa Chat y agentes]] · 366 líneas · `core/canvas_spec.py`

## Para qué sirve

Canvas IA: criterio de tipo de gráfico + validación.

## API pública

- `time_like(labels)` _(línea 92)_
- `sanitize_hints(raw)` — Hints del navegador → dict acotado y seguro (o {}). _(línea 97)_
- `hints_prompt(h)` — Bloque del prompt con la consulta YA PARSEADA por el router del cliente. _(línea 139)_
- `validate_spec(spec, hints=…, query=…)` — Normaliza la spec de la IA. Devuelve (spec, fixes). Lanza ValueError si no queda nada dibujable (el endpoint responde 502 y el cliente cae … _(línea 182)_

**Internas** (empiezan con `_`): `_num`, `_clean_num`, `_infer_type`

## Depende de

_Nada interno._

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_canvas.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-03 — GASTO DE IA, SIM. ESTRUCTURAL, AVATARES, CANVAS, COMITÉ DE CARTERA]]
