---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_block0_committee.py"
lenguaje: "python"
lineas: 133
aliases: ["tests/test_block0_committee.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_block0_committee.py

> Prueba · capa [[Capa Pruebas]] · 133 líneas · `tests/test_block0_committee.py`

## Qué prueba

Bloque 0 (docs/BRECHAS_V2.md) — matemática del comité, confianza y cartera: L2-05 (mitad "no validado" aunque muerda el tope), L2-06 (convicción por analista, no por claim), L2-08 (independencia por proveedor), L2-17 (mismo denominador para riesgo y peso), L2-19 (unidades declaradas, sin adivinar).

**9** funciones `test_…`.

## Cubre

- [[core.portfolio_advisor.py]]
- [[research.analytics.py]]
- [[research.committee.py]]
- [[research.confidence.py]]
