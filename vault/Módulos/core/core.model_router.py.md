---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/model_router.py"
lenguaje: "python"
lineas: 89
aliases: ["core/model_router.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/model_router.py

> Módulo · capa [[Capa Infraestructura]] · 89 líneas · `core/model_router.py`

## Para qué sirve

ROUTER DE MODELOS del chat (2026-11-07, pedido de Fabrizio: «request → router → modelo pequeño / mediano / frontera, y que ese router sea Jev»).

## API pública

- `enabled()` _(línea 42)_
- `models()` _(línea 46)_
- `from_jev(plan)` — Ruta de Jev → carril (None si Jev no decidió). _(línea 53)_
- `from_rules(message, context=…)` — Respaldo instantáneo cuando Jev no llega: reglas fijas sobre el texto (sin IA). _(línea 67)_
- `choose(plan, message, context=…)` _(línea 80)_

## Depende de

- [[core.config.py]] — importa `AI_MODEL_FAST`

## Lo usan

- [[core.khipu_chat.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV AI_MODEL_FRONTIER]]
- [[ENV AI_MODEL_SMALL]]
- [[ENV AI_ROUTER]]

## Pruebas que lo cubren

- [[tests.test_model_router.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
