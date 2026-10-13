---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "engine/portfolios.js"
lenguaje: "javascript"
lineas: 1371
aliases: ["engine/portfolios.js"]
tags: ["capa/dinero", "tipo/modulo"]
---

# engine/portfolios.js

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 1.371 líneas · `engine/portfolios.js`

## Para qué sirve

🧪 CARTERAS SIMULADAS (paper trading local)

## API pública (globales que define)

`window.KhipuPortfolios`

## Depende de

- [[engine.app_main.js]] — usa `LANG`, `MKT`, `NODE_BY_ID`, `fetchQuotes`
- [[engine.explain.js]] — usa `explainChip`, `explainRegister`
- [[engine.mascot.js]] — usa `KhipuMascot`
- [[engine.resolve.js]] — usa `KhipuResolve`
- [[engine.riskreport.js]] — usa `KhipuRisk`
- [[engine.toast.js]] — usa `KhipuToast`
- [[nodes.nodes_seed.js]] — usa `NODES`, `NODE_META`
- [[nodes.preipo_intel.js]] — usa `PREIPO_INTEL`

Se carga en [[app.html]] en la posición **85 de 97** (línea 3142), después de [[engine.crypto.js]] y antes de [[engine.oswindows.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 85)
- [[engine.app_main.js]] — usa `KhipuPortfolios`
- [[engine.cockpit.js]] — usa `KhipuPortfolios`
- [[engine.khipu_chat.js]] — usa `KhipuPortfolios`
- [[engine.pfcommittee.js]] — usa `KhipuPortfolios`
- [[engine.riskreport.js]] — usa `KhipuPortfolios`
- [[engine.sync.js]] — usa `KhipuPortfolios`

## Endpoints que llama

- `GET /api/portfolio-ai/themes` → [[core.portfolio_ai.py]] ([[API portfolio-ai]])
- `POST /api/portfolio-ai/ask` → [[core.portfolio_ai.py]] ([[API portfolio-ai]])
- `POST /api/portfolio-ai/propose` → [[core.portfolio_ai.py]] ([[API portfolio-ai]])

## Pruebas que lo cubren

- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_overnight_ui_portfolios_risk.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-10-03 (c) — TERMINAL REDISEÑADA + POP-UPS DE COMPRA-VENTA (sw v182)]]
- [[Sesión 2026-07-13 — Etapa O — Khipus Finance AI - 9 frentes + rebrand + Cabina inicial]]
