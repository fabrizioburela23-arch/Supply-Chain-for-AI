---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-14"
ruta: "docs/ESTADO.md#L181"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-14 (b) — LOTE J: SERVIDOR A 5.000 + CHAT PROGRESIVO (F3) + revisión — sw v270

> Sesión de trabajo · `docs/ESTADO.md` línea 181 (18 líneas) · [[Índice de sesiones]]

## Resumen

\- Escala (EXPANSION_5K E0/E1, menos E1.6): kernel disperso (0 diferencias a 937/5k/10k/20k), tensor sin matrices densas, vistas con ≤ 2 generaciones, una reconstrucción por versión, búsqueda por índice, paginación, D-1/D-2 (+ parte de D-3). Banco: `python scripts/bench_scale.py --n 5000 --repeat 3`; prueba lenta con `KH_SCALE=1`. - Medido a 5k (sintético, 5.032 ids): Impact 105-137 ms · tensor 96-141 ms · ficha p50 0,4 ms · primera ficha tras una

## Archivos que menciona

- [[engine.genui_progress.js]]
- [[scripts.bench_scale.py]]

← más antigua: [[Sesión 2026-10-14 — RESPUESTAS VISUALES F2 - revisión (19 hallazgos) — sw v269]] · más nueva: [[Sesión 2026-10-14 (c) — LOTE K - IMPORTADOR DE EMPRESAS, PAÍSES ISO-2, CATEGORÍAS, CHAT]] →
