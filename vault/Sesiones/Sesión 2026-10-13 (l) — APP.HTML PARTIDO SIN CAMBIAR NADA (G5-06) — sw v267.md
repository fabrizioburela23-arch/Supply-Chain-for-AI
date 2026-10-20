---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-13"
ruta: "docs/ESTADO.md#L216"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-13 (l) — APP.HTML PARTIDO SIN CAMBIAR NADA (G5-06) — sw v267

> Sesión de trabajo · `docs/ESTADO.md` línea 216 (26 líneas) · [[Índice de sesiones]]

## Resumen

\- Fabrizio: «si, sigue con app.html, con cuidado». app.html 12.682 → 3.463 líneas (766 KB → 231 KB): 6 de sus 10 bloques `&lt;script>` inline (96 % del JS) pasaron BYTE A BYTE a engine/app_main.js (núcleo), app_coordinator.js, app_trade_panel.js, app_preflight.js, app_canvas.js y app_scatter.js, cada uno con un `&lt;script src>` clásico en el MISMO lugar (mismo orden, mismo ámbito global; el servidor les pone ?v=N y van al SHELL de sw.js).

## Archivos que menciona

- [[app.html]]
- [[engine.app_canvas.js]]
- [[engine.app_coordinator.js]]
- [[engine.app_main.js]]
- [[engine.app_preflight.js]]
- [[engine.app_scatter.js]]
- [[engine.app_trade_panel.js]]
- [[sw.js]]
- [[tests.test_app_split.py]]

← más antigua: [[Sesión 2026-10-13 (k) — FASE 2+ LOTE I - rutas con decisión, CSP estricta, riesgo]] · más nueva: [[Sesión 2026-10-13 (m) — app.html PARTIDO + 2 arreglos visibles — sw v268]] →
