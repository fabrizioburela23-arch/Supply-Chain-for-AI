---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-15"
ruta: "docs/ESTADO.md#L102"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-15 b — REVISIÓN DE «UN SOLO LUGAR»: NADA SE PIERDE ENTRE DISPOSITIVOS — sw v275

> Sesión de trabajo · `docs/ESTADO.md` línea 102 (18 líneas) · [[Índice de sesiones]]

## Resumen

\- 🔒 \*\*Tres casos raros en que unas posiciones podían perderse, arreglados\*\* (`engine/pfstore.js` + `engine/sync.js`): - una pestaña vieja (sin recargar) o un teléfono recién vinculado traen un `eco_pos` que no es copia de ninguna cartera → `KhipuPfStore.fromServer` lo \*\*adopta\*\* en «Mi cartera» (o crea una) ANTES de reescribir la copia; copias atrasadas que este navegador ya vio (`kh_pos_seen`, solo local) no se adoptan (no duplica);

## Archivos que menciona

- [[engine.pfstore.js]]
- [[engine.sync.js]]
- [[tests.test_one_portfolio_store.py]]

← más antigua: [[Sesión 2026-10-15 — UN SOLO LUGAR DONDE GUARDAR (carteras) — sw v274]] · más nueva: [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]] →
