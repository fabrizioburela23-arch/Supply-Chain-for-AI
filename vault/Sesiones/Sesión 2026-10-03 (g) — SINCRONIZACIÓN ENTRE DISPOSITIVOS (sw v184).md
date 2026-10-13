---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-03"
ruta: "docs/ESTADO.md#L1022"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-03 (g) — SINCRONIZACIÓN ENTRE DISPOSITIVOS (sw v184)

> Sesión de trabajo · `docs/ESTADO.md` línea 1022 (11 líneas) · [[Índice de sesiones]]

## Resumen

\- `engine/sync.js` (NUEVO, window.KhipuSync): sincroniza kh_portfolios, kh_pf_active, kh_investor_profile y eco_pos (MKT.pos) con el servidor; parchea Storage.prototype.setItem para subir cada cambio (1,5 s), baja al abrir, cada 2 min y al volver a la pestaña; último que escribe gana (kh_sync_meta). Vincular otro dispositivo = pegar el código (la llave kh_owner_key) en Comité → 💼 Mi cartera → 📱 Otros dispositivos.

## Archivos que menciona

- [[Doc CLAUDE]]
- [[core.portfolio_reports_api.py]]
- [[engine.sync.js]]

← más antigua: [[Sesión 2026-10-03 (f) — PANEL DE TRADING BILINGÜE Y MÓVIL + APROBACIÓN DEL COMITÉ CON]] · más nueva: [[Sesión 2026-10-04 — ESCRITORIO KHIPU K1 - VENTANAS DENTRO DE LA CABINA (sw v186)]] →
