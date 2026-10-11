---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_cleanup_nrs_parity.py"
lenguaje: "python"
lineas: 80
aliases: ["tests/test_cleanup_nrs_parity.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_cleanup_nrs_parity.py

> Prueba · capa [[Capa Pruebas]] · 80 líneas · `tests/test_cleanup_nrs_parity.py`

## Qué prueba

Limpieza 2026-10-11 (§2 del inventario de "cosas sueltas"): el NRS tenía 5 copias con divergencia REAL — el servidor omitía el término fundamental (hasta 15 pts en 370/937 empresas) y Python redondeaba al par (457/937 empresas con término de mercado terminado en .5 → 1 punto menos). Ahora hay UNA fórmula por lenguaje: app.html `_nrsTerms` y core/world.py `client_nrs` (servidor, MCP y carteras delegan ahí). Esta prueba ejecuta la del navegador sobre TODO el catálogo y exige el MISMO número que la de Python, empresa por empresa.

**3** funciones `test_…`.

## Cubre

- [[app.html]]
- [[core.live_fundamentals.py]]
- [[core.portfolio_ai.py]]
- [[core.world.py]]
- [[data.grafo_v0.json]]
- [[ontology.agents.py]]
- [[ontology.vocabulary.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-11 (b) — LIMPIEZA QUE NO QUEDEN COSAS SUELTAS (sw v254)]]
