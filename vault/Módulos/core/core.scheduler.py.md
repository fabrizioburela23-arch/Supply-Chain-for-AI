---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/scheduler.py"
lenguaje: "python"
lineas: 105
aliases: ["core/scheduler.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/scheduler.py

> Módulo · capa [[Capa Infraestructura]] · 105 líneas · `core/scheduler.py`

## Para qué sirve

tareas periódicas del SERVIDOR (misión de reparación 2026-10-04, R5).

## API pública

- `register(name, fn, every_s, run_at_start=…)` — Registra (o reemplaza) una tarea. run_at_start: la primera pasada la corre. _(línea 33)_
- `tick(now=…)` — Una pasada: corre las tareas vencidas (testable, sin hilo). _(línea 41)_
- `state()` _(línea 63)_
- `enabled()` _(línea 70)_
- `start()` — Arranca el hilo (una vez). Devuelve True si quedó corriendo. _(línea 83)_
- `running()` _(línea 97)_

**Internas** (empiezan con `_`): `_iso`, `_loop`, `_reset`

## Depende de

_Nada interno._

## Lo usan

- [[core.ops_check.py]] — lo importa
- [[research.health.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV KHIPU_SCHEDULER]]

## Pruebas que lo cubren

- [[tests.test_repair_committee.py]]
- [[tests.test_repair_research.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-04 (h) — MISIÓN DE REPARACIÓN P0 INVESTIGACIÓN (R1-R6, sw v201)]]
