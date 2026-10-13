---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-12"
ruta: "docs/ESTADO.md#L189"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-12 (e) — BLOQUE 0 DE BRECHAS_V2: CIFRAS Y PUBLICACIÓN SEGURAS

> Sesión de trabajo · `docs/ESTADO.md` línea 189 (13 líneas) · [[Índice de sesiones]]

## Resumen

\- Guardián de cifras (core/numbers.py) reescrito: recall 0,08 → 0,98 y precisión 0,94 en un corpus de 102 respuestas ES/EN (las 3 marcas "de más" son cifras DERIVADAS por la IA, que se rechazan a propósito). Formatos de la app ("233,95 USD", "dólares", monedas no-USD), comparación por tipo contra los datos, signo, tramo exacto, sin regex cuadráticas (antes un texto de dígitos podía congelar el único worker). Regla 8 de los analistas cubre todas las cifras.

## Archivos que menciona

- [[core.numbers.py]]

← más antigua: [[Sesión 2026-10-12 (d) — INFRAESTRUCTURA OPERATIVA - DECISIONES, PUERTAS SHACL, VISTAS]] · más nueva: [[Sesión 2026-10-13 — INFRAESTRUCTURA OPERATIVA, PASOS 1-4]] →
