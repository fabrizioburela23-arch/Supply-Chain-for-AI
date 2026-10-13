---
tipo: "prueba"
capa: "Pruebas"
ruta: "tests/test_config_env_strip.py"
lenguaje: "python"
lineas: 40
aliases: ["tests/test_config_env_strip.py"]
tags: ["capa/pruebas", "tipo/prueba"]
---

# tests/test_config_env_strip.py

> Prueba · capa [[Capa Pruebas]] · 40 líneas · `tests/test_config_env_strip.py`

## Qué prueba

Variables de modelo pegadas en Railway con saltos de línea o espacios (2026-10-13: AI_MODEL_DEEP llegó como 'claude-sonnet-5-5\n\n\n\n') no deben convertirse en un id de modelo inválido; y el respaldo Pro de Gemini usa su id real (gemini-3.1-pro-preview).

**3** funciones `test_…`.

## Cubre

- [[core.config.py]]

## Variables de entorno que fija o nombra

[[ENV GEMINI_FALLBACK_MODEL]]
