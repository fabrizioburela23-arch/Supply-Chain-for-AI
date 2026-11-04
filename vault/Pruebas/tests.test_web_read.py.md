---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_web_read.py"
lenguaje: "python"
lineas: 81
aliases: ["tests/test_web_read.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_web_read.py

> Prueba · capa [[Capa Pruebas]] · 81 líneas · `tests/test_web_read.py`

## Qué prueba

el chat busca y LEE la web sin Tavily (2026-11-04): las herramientas de servidor de Anthropic (web_search / web_fetch) con la MISMA ANTHROPIC_KEY, por core/ai.py (control de gasto, cupo y corta-circuito de siempre).

**4** funciones `test_…`.

## Cubre

- [[core.ai.py]]
- [[core.khipu_chat.py]]
- [[core.websearch.py]]

## Variables de entorno que fija o nombra

[[ENV SECRET_KEY]], [[ENV TAVILY_KEY]]
