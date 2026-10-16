---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-13"
ruta: "docs/ESTADO.md#L360"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-13 (g-rev) — REVISIÓN DEL BATCH G (12 hallazgos, todos corregidos con prueba)

> Sesión de trabajo · `docs/ESTADO.md` línea 360 (20 líneas) · [[Índice de sesiones]]

## Resumen

\- G(t, κ): `props_at` pliega en orden de REGISTRO (el de `_materialize`): una corrección retroactiva registrada después ya no queda tapada; `_links_active_at(None, κ)` = semántica de la TABLA (κ = ahora es EXACTAMENTE el grafo vivo, también con vínculos con ventana o fechados a futuro); `Known.key()` lleva la marca de huérfanos (eventos económicos sin versión) → la LRU AsOf y el índice de nodos ya no sirven otro grafo. Prueba: tests/test_bitemporal_review.py.

## Archivos que menciona

- [[tests.test_bitemporal_review.py]]
- [[tests.test_review_batch_g.py]]

## Variables que menciona

[[ENV ALPACA_BASE]]

← más antigua: [[Sesión 2026-10-13 (e) — PASOS 18-21 Y BLOQUES 4-5]] · más nueva: [[Sesión 2026-10-13 (f) — PASOS 22, 23, 25, 26 Y 11]] →
