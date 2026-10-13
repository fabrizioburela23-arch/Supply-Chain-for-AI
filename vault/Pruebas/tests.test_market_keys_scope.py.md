---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_market_keys_scope.py"
lenguaje: "python"
lineas: 18
aliases: ["tests/test_market_keys_scope.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_market_keys_scope.py

> Prueba · capa [[Capa Pruebas]] · 18 líneas · `tests/test_market_keys_scope.py`

## Qué prueba

La ventana de Mercado mostraba «Error al obtener precios: Keys is not defined» (2026-10-13, hallado al partir app.html): fetchQuotes usaba `Keys`, que solo existe dentro del IIFE de V8. Debe leerse por window.V8.Keys.

**1** funciones `test_…`.

## Cubre

- [[engine.app_main.js]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (m) — app.html PARTIDO + 2 arreglos visibles — sw v268]]
