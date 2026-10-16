---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-13"
ruta: "docs/ESTADO.md#L241"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-13 (j) — ESPACIO: VUELVEN LOS SATÉLITES (arreglo urgente) — sw v265

> Sesión de trabajo · `docs/ESTADO.md` línea 241 (13 líneas) · [[Índice de sesiones]]

## Resumen

\- Fabrizio: «¿por qué la del espacio ya no tiene los satélites?». El código que DIBUJA no cambió; fallaba traer los datos y verlos: (1) el servidor pedía a CelesTrak 11 grupos en serie (12 s c/u) sin parar ante errores ni guardar respaldos → hasta 132 s sin satélites y descargas repetidas que hacen que CelesTrak bloquee la IP (403 si se repite un grupo en <2 h); (2) la regla global `.sm` de spacemonitor.js estiraba el chip «Crear cartera» (`span.v.sm`) a 520 px y tapaba el

## Archivos que menciona

- [[core.celestrak.py]]
- [[engine.spacemonitor.js]]
- [[tests.test_space_satellites.py]]

← más antigua: [[Sesión 2026-10-13 (i) — NEO4J RETIRADO (decisión 6 de Fabrizio) — sw v264]] · más nueva: [[Sesión 2026-10-13 (k) — FASE 2+ LOTE I - rutas con decisión, CSP estricta, riesgo]] →
