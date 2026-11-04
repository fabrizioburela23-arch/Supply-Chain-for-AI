---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_crypto_symbol_normalize.py"
lenguaje: "python"
lineas: 19
aliases: ["tests/test_crypto_symbol_normalize.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_crypto_symbol_normalize.py

> Prueba · capa [[Capa Pruebas]] · 19 líneas · `tests/test_crypto_symbol_normalize.py`

## Qué prueba

una venta de «ETHUSD» (símbolo de POSICIÓN de Alpaca, sin barra) salía con tif 'day' y Alpaca la rechazaba: «invalid crypto time_in_force» (orden real fallida, 2026-10-30). Ahora la validación de la orden (el único lugar: brokerage.service._spec) convierte las bases de cripto conocidas a su par y fuerza gtc.

**2** funciones `test_…`.

## Cubre

- [[brokerage.service.py]]
