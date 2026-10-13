---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_jev_status_label.py"
lenguaje: "python"
lineas: 26
aliases: ["tests/test_jev_status_label.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_jev_status_label.py

> Prueba · capa [[Capa Pruebas]] · 26 líneas · `tests/test_jev_status_label.py`

## Qué prueba

El 💰 Gasto IA decía «MODO SOMBRA» aunque Jev ya mandaba en el chat (Fabrizio, 2026-10-13: «modo sombra dice, ¿qué significa?»). /api/decide/status expone control_features y la UI dice «ACTIVO · manda en el chat».

**3** funciones `test_…`.

## Cubre

- [[core.decide_api.py]]
- [[engine.aispend.js]]
- [[server.py]]

## Rutas HTTP que llama

1 rutas, de los grupos: [[API decide]]

## Variables de entorno que fija o nombra

[[ENV DECIDE_CONTROL]], [[ENV TYPESAFE_API_KEY]], [[ENV TYPESAFE_KEY]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (m) — app.html PARTIDO + 2 arreglos visibles — sw v268]]
