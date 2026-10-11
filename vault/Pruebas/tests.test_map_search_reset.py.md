---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_map_search_reset.py"
lenguaje: "python"
lineas: 23
aliases: ["tests/test_map_search_reset.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_map_search_reset.py

> Prueba · capa [[Capa Pruebas]] · 23 líneas · `tests/test_map_search_reset.py`

## Qué prueba

Mapa (2026-10-05): buscar una empresa, elegirla y deseleccionarla dejaba encendida SOLO esa empresa hasta recargar. Causa: pickSugg limpiaba searchTerm pero no el filtro guardado (buildFilterCache seguía con "nvid").

**2** funciones `test_…`.

## Cubre

- [[app.html]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (y) — NRS ACOTADO + BÚSQUEDA DEL MAPA (sw v232)]]
