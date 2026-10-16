---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-13"
ruta: "docs/ESTADO.md#L193"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-13 (m) — app.html PARTIDO + 2 arreglos visibles — sw v268

> Sesión de trabajo · `docs/ESTADO.md` línea 193 (14 líneas) · [[Índice de sesiones]]

## Resumen

\- app.html 12.682 → 3.463 líneas: 6 de 10 bloques &lt;script> movidos BYTE A BYTE a engine/app_main.js, app_coordinator.js, app_trade_panel.js, app_preflight.js, app_canvas.js y app_scatter.js, cada uno en el MISMO lugar (sin defer/async). Quedan inline: el bloque 1 (arranque de emergencia, seguridad del cliente, franja «servidor no disponible»), el 4 (vigía de /api/health), el orbe (3,9 KB) y la insignia de clientes (0,7 KB). CSS sin tocar. Paridad en Chromium antes/después:

## Archivos que menciona

- [[app.html]]
- [[engine.app_canvas.js]]
- [[engine.app_coordinator.js]]
- [[engine.app_main.js]]
- [[engine.app_preflight.js]]
- [[engine.app_scatter.js]]
- [[engine.app_trade_panel.js]]
- [[sw.js]]
- [[tests._app_source.py]]
- [[tests.test_jev_status_label.py]]
- [[tests.test_market_keys_scope.py]]

← más antigua: [[Sesión 2026-10-13 (l) — APP.HTML PARTIDO SIN CAMBIAR NADA (G5-06) — sw v267]] · más nueva: [[Sesión 2026-10-14 — RESPUESTAS VISUALES F2 - revisión (19 hallazgos) — sw v269]] →
