---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-05"
ruta: "docs/ESTADO.md#L1161"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-05 (t) — ESTRECHOS Y PAÍSES: CURADO + EN VIVO (sw v226)

> Sesión de trabajo · `docs/ESTADO.md` línea 1161 (8 líneas) · [[Índice de sesiones]]

## Resumen

\- `_blend_live_chokepoint` / `_blend_live_country` (core/world.py): las capas curadas leen la caché de las capas vivas (sin descargar): estrecho = máx(curado, caída de buques FMI PortWatch) + `live_shipping`; país = máx(curado, aviso oficial nivel 3-4) + hasta +10 por eventos de conflicto/protesta GDELT 24 h en el país (`advisory_level`, `live_events`). Estado de la capa: `live_inputs` → la UI dice "curado + vivo".

## Archivos que menciona

- [[core.world.py]]

← más antigua: [[Sesión 2026-10-05 (s) — CARTERA CONTEXTO, AGENTE QUIÉN RESPONDE (sw v225)]] · más nueva: [[Sesión 2026-10-05 (u) — ÍNDICE GPR (Caldara-Iacoviello) EN VIVO (sw v227)]] →
