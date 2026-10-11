---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/logjson.py"
lenguaje: "python"
lineas: 81
aliases: ["core/logjson.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/logjson.py

> Módulo · capa [[Capa Infraestructura]] · 81 líneas · `core/logjson.py`

## Para qué sirve

O2 (misión de reparación 2026-10-04): logs estructurados.

## API pública

- `enabled()` _(línea 28)_
- `current_fields()` _(línea 32)_
- `log_context(**fields)` _(línea 37)_
- clase `JsonFormatter` _(línea 46)_
- `configure(root=…)` — Llamar una vez tras logging.basicConfig. Devuelve True si activó JSON. _(línea 60)_
- `event(name, level=…, **fields)` — Evento estructurado (solo con LOG_JSON=on: en modo texto no ensucia los logs). _(línea 73)_

## Depende de

_Nada interno._

## Lo usan

- [[core.ai_usage.py]] — lo importa
- [[research.runner.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV LOG_JSON]]

## Pruebas que lo cubren

- [[tests.test_repair_logs.py]]
