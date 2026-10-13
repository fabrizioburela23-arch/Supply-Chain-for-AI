---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_csp_estricta.py"
lenguaje: "python"
lineas: 111
aliases: ["tests/test_csp_estricta.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_csp_estricta.py

> Prueba · capa [[Capa Pruebas]] · 111 líneas · `tests/test_csp_estricta.py`

## Qué prueba

G5-09 (lote I1): la Content-Security-Policy de server.py sin 'unsafe-eval' y con connect-src cerrado a los hosts que el navegador llama de verdad.

**4** funciones `test_…`.

## Cubre

- [[app.html]]
- [[core.voice_agent.py]]
- [[server.py]]
- [[sw.js]]

## Rutas HTTP que llama

1 rutas, de los grupos: [[API vocabulary]]

## Variables de entorno que fija o nombra

[[ENV SECRET_KEY]]
