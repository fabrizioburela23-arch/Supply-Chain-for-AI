---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_chat_portfolio_agent.py"
lenguaje: "python"
lineas: 141
aliases: ["tests/test_chat_portfolio_agent.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_chat_portfolio_agent.py

> Prueba · capa [[Capa Pruebas]] · 141 líneas · `tests/test_chat_portfolio_agent.py`

## Qué prueba

El comité de cartera DENTRO del chat (2026-10-05: "/cartera dime si debería reducir…" solo abría una pantalla y no respondía). POST /api/committee/portfolio/ask mide la cartera y el cerebro contesta con ese análisis como contexto verificado.

**3** funciones `test_…`.

## Cubre

- [[core.khipu_chat.py]]
- [[core.portfolio_advisor.py]]
- [[engine.agents_registry.js]]
- [[engine.khipu_chat.js]]
- [[research.committee_api.py]]
- [[server.py]]

## Rutas HTTP que llama

1 rutas, de los grupos: [[API committee]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (r) — RESPUESTA ENFOCADA EN LA CARTERA + UN ANALISTA CONCRETO SOBRE TU]]
- [[Sesión 2026-10-05 (o) — AGENTES CON CHIP EN EL CHAT - EL COMITÉ DE CARTERA RESPONDE AHÍ]]
