---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_broker_sleeves.py"
lenguaje: "python"
lineas: 75
aliases: ["tests/test_broker_sleeves.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_broker_sleeves.py

> Prueba · capa [[Capa Pruebas]] · 75 líneas · `tests/test_broker_sleeves.py`

## Qué prueba

Carteras sobre UNA cuenta de Alpaca (brokerage/sleeves, fase 2): contabilidad por cartera y control previo a la orden (comprar ≤ efectivo disponible; vender ≤ lo que es suyo).

**5** funciones `test_…`.

## Cubre

- [[brokerage.alpaca.py]]
- [[brokerage.service.py]]
- [[brokerage.sleeves.py]]
