---
tipo: "modulo"
capa: "Interfaz (Khipus OS)"
ruta: "engine/explain.js"
lenguaje: "javascript"
lineas: 419
aliases: ["engine/explain.js"]
tags: ["capa/interfaz", "tipo/modulo"]
---

# engine/explain.js

> Módulo · capa [[Capa Interfaz (Khipus OS)]] · 419 líneas · `engine/explain.js`

## Para qué sirve

EXPLICADOR DE MÉTRICAS para no expertos (2026-07-12). Feedback real: un inversionista preguntó "¿qué es el NRS y cómo se calcula?" y la app no se lo decía. Regla nueva: toda métrica tiene su "?" que la explica en lenguaje simple — en ESPAÑOL e INGLÉS (regla bilingüe).

## API pública (globales que define)

`window.explainChip`, `window.explainMetric`, `window.explainRegister`

## Depende de

- [[app.html]] — usa `LANG`

Se carga en [[app.html]] en la posición **77 de 97** (línea 7936), después de [[engine.termdata.js]] y antes de [[engine.reconcile.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 77)
- [[app.html]] — usa `explainChip`, `explainMetric`
- [[engine.audit.js]] — usa `explainChip`
- [[engine.clients.js]] — usa `explainChip`, `explainRegister`
- [[engine.cockpit.js]] — usa `explainMetric`
- [[engine.committee.js]] — usa `explainChip`, `explainRegister`
- [[engine.fincard.js]] — usa `explainChip`
- [[engine.governance.js]] — usa `explainChip`
- [[engine.insights.js]] — usa `explainMetric`
- [[engine.mcpconnect.js]] — usa `explainChip`, `explainRegister`
- [[engine.oswindows.js]] — usa `explainMetric`, `explainRegister`
- [[engine.pfcommittee.js]] — usa `explainMetric`
- [[engine.portfolios.js]] — usa `explainChip`, `explainRegister`
- [[engine.pricehist.js]] — usa `explainChip`, `explainRegister`
- [[engine.reconcile.js]] — usa `explainChip`, `explainRegister`
- [[engine.research.js]] — usa `explainChip`
- [[engine.riskreport.js]] — usa `explainChip`, `explainRegister`
- [[engine.spacemonitor.js]] — usa `explainChip`, `explainRegister`
- [[engine.termdata.js]] — usa `explainChip`
- [[engine.worldmonitor.js]] — usa `explainChip`, `explainRegister`
- [[engine.xray.js]] — usa `explainChip`, `explainMetric`

## Pruebas que lo cubren

- [[tests.test_cierre_defectos.py]]
- [[tests.test_no_client_engine.py]]
- [[tests.test_options_greeks_totals.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_scenario_pnl_browser.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-13 (h) — PASO 24 - REPETIR DECISIONES (replay), IMPLEMENTACIONES RETENIDAS]]
- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-09-29 (día) — REPORTE DE RIESGO - VaR + VEGA-KAPPA (sw v164)]]
- [[Sesión 2026-07-12 — Etapa H — Feedback 7 - explicabilidad + regla bilingüe + cripto]]
