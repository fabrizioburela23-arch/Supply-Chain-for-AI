---
tipo: "modulo"
capa: "Infraestructura"
ruta: "scripts/build_impl_goldens.py"
lenguaje: "python"
lineas: 74
aliases: ["scripts/build_impl_goldens.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# scripts/build_impl_goldens.py

> Módulo · capa [[Capa Infraestructura]] · 74 líneas · `scripts/build_impl_goldens.py`

## Para qué sirve

salidas DORADAS de las implementaciones retenidas (core/impls.py; INFRA §5.2, paso 24).

## API pública

- `path_of(key, version)` _(línea 33)_
- `compute(key, version)` _(línea 37)_
- `main(check=…)` _(línea 47)_

## Depende de

- [[core.impls.py]] — importa `impls`

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

## Pruebas que lo cubren

- [[tests.test_impl_registry.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (h) — PASO 24 - REPETIR DECISIONES (replay), IMPLEMENTACIONES RETENIDAS]]
