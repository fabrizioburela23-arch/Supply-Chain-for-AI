---
tipo: "modulo"
capa: "Cuantitativo (matrices, tensores, riesgo)"
ruta: "engine/riskreport.js"
lenguaje: "javascript"
lineas: 992
aliases: ["engine/riskreport.js"]
tags: ["capa/cuantitativo", "tipo/modulo"]
---

# engine/riskreport.js

> Módulo · capa [[Capa Cuantitativo (matrices, tensores, riesgo)]] · 992 líneas · `engine/riskreport.js`

## Para qué sirve

REPORTE DE RIESGO DE CARTERA: VaR + Vega (Kappa).

## API pública (globales que define)

`window.KhipuRisk`

## Depende de

- [[app.html]] — usa `BASE`, `DataLayer`, `LANG`, `MKT`, `NODE_BY_ID`
- [[engine.explain.js]] — usa `explainChip`, `explainRegister`
- [[engine.mascot.js]] — usa `KhipuMascot`
- [[engine.portfolios.js]] — usa `KhipuPortfolios`
- [[nodes.nodes_seed.js]] — usa `NODES`

Se carga en [[app.html]] en la posición **53 de 95** (línea 7903), después de [[engine.research.js]] y antes de [[engine.worldmonitor.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 53)
- [[app.html]] — usa `KhipuRisk`
- [[engine.cockpit.js]] — usa `KhipuRisk`
- [[engine.khipu_chat.js]] — usa `KhipuRisk`
- [[engine.khipu_lang.js]] — usa `KhipuRisk`
- [[engine.portfolios.js]] — usa `KhipuRisk`

## Endpoints que llama

- `GET /api/options/chain/<symbol>` → [[server.py]] ([[API options]])
- `POST /api/portfolio/risk_report` → [[server.py]] ([[API portfolio]])
- `POST /api/portfolio/vega_report` → [[server.py]] ([[API portfolio]])

## Pruebas que lo cubren

- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_overnight_ui_portfolios_risk.py]]
- [[tests.test_review_batch_e.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-09-30 al 10-02 — MONITORES, RIESGO FÁCIL, ASISTENTE, CEREBRO DE KHIPU]]
- [[Sesión 2026-09-29 (día) — REPORTE DE RIESGO - VaR + VEGA-KAPPA (sw v164)]]
