---
tipo: "sesion"
capa: "Documentación"
fecha: "2026-10-04"
ruta: "docs/ESTADO.md#L757"
tags: ["capa/documentacion", "tipo/sesion"]
---

# SESIÓN 2026-10-04 (b) — ESCRITORIO: REVISIÓN ADVERSARIAL Y CORRECCIONES (sw v187)

> Sesión de trabajo · `docs/ESTADO.md` línea 757 (31 líneas) · [[Índice de sesiones]]

## Resumen

Workflow de revisión (5 lentes × 2 refutadores por hallazgo, 61 agentes): 20 hallazgos confirmados, 8 rechazados. Corregido TODO lo confirmado (engine/desktop.js reescrito; cockpit.js): - GRAVE: bucle de `resize` sintético a 5 Hz (onResize → fireResize → resize → onResize…) que seguía con la Cabina cerrada y hacía settleGraph del mapa sin parar. Ahora onResize ignora `isTrusted=false`

## Archivos que menciona

- [[engine.cockpit.js]]
- [[engine.desktop.js]]

← más antigua: [[Sesión 2026-10-04 — ESCRITORIO KHIPU K1 - VENTANAS DENTRO DE LA CABINA (sw v186)]] · más nueva: [[Sesión 2026-10-04 (c) — JEV (TYPESAFE) EN MODO SOMBRA - PORTERO DEL CHAT (sw v188)]] →
