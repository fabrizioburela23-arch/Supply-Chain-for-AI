---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-05"
ruta: "docs/ESTADO.md#L1058"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-05 (x) — CIFRAS VIEJAS → VERIFICADAS / EN VIVO (sw v231)

> Sesión de trabajo · `docs/ESTADO.md` línea 1058 (19 líneas) · [[Índice de sesiones]]

## Resumen

\- Auditoría (agente Explore) de cifras fijas en la UI: ~40 hallazgos. Hechos los de mayor riesgo: · app.html `applyVerifiedValuations()` (al cargar y en DOMContentLoaded, idempotente): NODE_META.mktcap_b, PREIPO_INTEL.valuation e INVEST_PATH.note de privadas = nodes/private_valuations.js (mktcap_verified {as_of,label,source_url}; mktcap_catalog/valuation_catalog guardan lo viejo); cotizadas → nota de

## Archivos que menciona

- [[app.html]]
- [[nodes.private_valuations.js]]
- [[tests.test_verified_valuations.py]]

← más antigua: [[Sesión 2026-10-05 (w) — REVISIÓN DEL WORLD MONITOR CON DATOS REALES (sw v229)]] · más nueva: [[Sesión 2026-10-05 (y) — NRS ACOTADO + BÚSQUEDA DEL MAPA (sw v232)]] →
