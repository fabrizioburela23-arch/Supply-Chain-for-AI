---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_gates_orders_parity.py"
lenguaje: "python"
lineas: 179
aliases: ["tests/test_gates_orders_parity.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_gates_orders_parity.py

> Prueba · capa [[Capa Pruebas]] · 179 líneas · `tests/test_gates_orders_parity.py`

## Qué prueba

INFRA_OPERATIVA paso 17: la puerta de ÓRDENES (governance/shapes/order.ttl, compilada en core/gates) dice EXACTAMENTE lo mismo que brokerage/risk.run_checks, control por control.

**4** funciones `test_…`.

## Cubre

- [[brokerage.risk.py]]
- [[brokerage.service.py]]
- [[core.__init__.py]]

## Variables de entorno que fija o nombra

[[ENV BROKERAGE_LIVE_ENABLED]], [[ENV BROKERAGE_TRADING_ENABLED]]
