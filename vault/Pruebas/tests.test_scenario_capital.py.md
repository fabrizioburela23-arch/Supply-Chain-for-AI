---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_scenario_capital.py"
lenguaje: "python"
lineas: 94
aliases: ["tests/test_scenario_capital.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_scenario_capital.py

> Prueba · capa [[Capa Pruebas]] · 94 líneas · `tests/test_scenario_capital.py`

## Qué prueba

Escenarios de FINANCIACIÓN (IPO / ronda, 2026-10-22, pedido de Fabrizio tras un informe «cualitativo» del chat sobre la salida a bolsa de OpenAI): el motor entiende «sale a bolsa» como evento de financiación con DOS casos (más pedidos / recorte de pedidos a los proveedores, % del kernel único aguas arriba), scenario_exposure entrega impact_pct y el impacto en la cartera (posiciones que pone el SERVIDOR) y el prompt prohíbe decir «no tengo modelo cuantitativo».

**6** funciones `test_…`.

## Cubre

- [[core.governance.py]]
- [[core.khipu_chat.py]]
- [[core.scenario_engine.py]]
- [[core.semantic.py]]
- [[mcp_server.ops.py]]

## Variables de entorno que fija o nombra

[[ENV SECRET_KEY]]
