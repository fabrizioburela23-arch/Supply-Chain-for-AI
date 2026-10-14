---
tipo: "modulo"
capa: "Infraestructura"
ruta: "scripts/build_impl_goldens.py"
lenguaje: "python"
lineas: 75
aliases: ["scripts/build_impl_goldens.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# scripts/build_impl_goldens.py

> Módulo · capa [[Capa Infraestructura]] · 75 líneas · `scripts/build_impl_goldens.py`

## Para qué sirve

salidas DORADAS de las implementaciones retenidas (core/impls.py; INFRA §5.2, paso 24).

## API pública

- `path_of(key, version)` _(línea 34)_
- `compute(key, version)` _(línea 38)_
- `main(check=…)` _(línea 48)_

## Depende de

- [[core.impls.py]] — importa `impls`

## Lo usan

_Nadie dentro de la app (ver_ [[01 Reporte del grafo]]_)._

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_impl_registry.py]]
- [[tests.test_import_governance.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (h) — PASO 24 - REPETIR DECISIONES (replay), IMPLEMENTACIONES RETENIDAS]]
