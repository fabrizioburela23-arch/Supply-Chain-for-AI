---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-05"
ruta: "docs/ESTADO.md#L1236"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-05 (m) — EL COMITÉ ANALIZA TODAS LAS POSICIONES (sw v215)

> Sesión de trabajo · `docs/ESTADO.md` línea 1236 (12 líneas) · [[Índice de sesiones]]

## Resumen

\- "No analizó todas mis posiciones, solo algunas": había un tope OCULTO de 30 (core/portfolio_advisor `_resolve_positions` y core/risk_report `build_report`); lo demás se descartaba sin aviso. Ahora `MAX_POSITIONS = 60` (build_report acepta `max_positions`; el MCP sigue en 30), lo que pase del tope y las privadas sin ticker van a `excluded` con

## Archivos que menciona

- [[core.portfolio_advisor.py]]
- [[core.risk_report.py]]
- [[engine.pfcommittee.js]]
- [[tests.test_portfolio_persist.py]]

← más antigua: [[Sesión 2026-10-05 (l) — CARTERAS QUE DESAPARECÍAN + COMITÉ DE CARTERA REGISTRADO (sw v214)]] · más nueva: [[Sesión 2026-10-05 (n) — GEOPOLÍTICA CON FUENTES OFICIALES (sw v216)]] →
