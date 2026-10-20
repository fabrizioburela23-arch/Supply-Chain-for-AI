---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_agent_signals_one_tap.py"
lenguaje: "python"
lineas: 130
aliases: ["tests/test_agent_signals_one_tap.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_agent_signals_one_tap.py

> Prueba · capa [[Capa Pruebas]] · 130 líneas · `tests/test_agent_signals_one_tap.py`

## Qué prueba

«1 toque» (2026-10-20): en modo MANUAL el agente PROPONE señales listas (lado, monto, precio visto, stop, motivo) y una persona las aprueba con su PIN; salen por EL camino único (brokerage.service.house_order, source='ui'). Vencen, no se usan dos veces y se rechazan si el precio se movió en contra. El agente ve además el técnico de cierres reales y la convicción de los analistas, con una guarda fija (no compra en sobrecompra extrema). Sin red y sin base (papel).

**9** funciones `test_…`.

## Cubre

- [[core.trading_agent.py]]
- [[engine.signals.js]]
- [[server.py]]

## Rutas HTTP que llama

3 rutas, de los grupos: [[API trade]]

## Variables de entorno que fija o nombra

[[ENV SECRET_KEY]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
