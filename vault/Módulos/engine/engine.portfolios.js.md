---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "engine/portfolios.js"
lenguaje: "javascript"
lineas: 1474
aliases: ["engine/portfolios.js"]
tags: ["capa/dinero", "tipo/modulo"]
---

# engine/portfolios.js

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 1.474 líneas · `engine/portfolios.js`

## Para qué sirve

🧪 CARTERAS SIMULADAS (paper trading local)

## API pública (globales que define)

`window.KhipuPortfolios`

## Depende de

- [[app.html]] — usa `_tradeFetch`, `_tradePinStored`
- [[engine.app_main.js]] — usa `LANG`, `MKT`, `NODE_BY_ID`, `fetchQuotes`
- [[engine.cockpit.js]] — usa `BixbyCockpit`
- [[engine.explain.js]] — usa `explainChip`, `explainRegister`
- [[engine.mascot.js]] — usa `KhipuMascot`
- [[engine.resolve.js]] — usa `KhipuResolve`, `_surface`
- [[engine.riskreport.js]] — usa `KhipuRisk`
- [[engine.toast.js]] — usa `KhipuToast`
- [[engine.trade.js]] — usa `_executeTradeOrder`, `_tradeAccountInfo`
- [[nodes.nodes_seed.js]] — usa `NODES`, `NODE_META`
- [[nodes.preipo_intel.js]] — usa `PREIPO_INTEL`

Se carga en [[app.html]] en la posición **89 de 105** (línea 3241), después de [[engine.crypto.js]] y antes de [[engine.genui.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 89)
- [[engine.app_main.js]] — usa `KhipuPortfolios`
- [[engine.cockpit.js]] — usa `KhipuPortfolios`
- [[engine.khipu_chat.js]] — usa `KhipuPortfolios`
- [[engine.pfcommittee.js]] — usa `KhipuPortfolios`
- [[engine.riskreport.js]] — usa `KhipuPortfolios`
- [[engine.sync.js]] — usa `KhipuPortfolios`

## Endpoints que llama

- `GET /api/portfolio-ai/themes` → [[core.portfolio_ai.py]] ([[API portfolio-ai]])
- `GET /api/trade/sleeves` → [[brokerage.sleeves.py]] ([[API trade]])
- `PATCH /api/trade/sleeves/<sleeve_id>` → [[brokerage.sleeves.py]] ([[API trade]])
- `POST /api/portfolio-ai/ask` → [[core.portfolio_ai.py]] ([[API portfolio-ai]])
- `POST /api/portfolio-ai/propose` → [[core.portfolio_ai.py]] ([[API portfolio-ai]])
- `POST /api/trade/sleeves/<sleeve_id>/archive` → [[brokerage.sleeves.py]] ([[API trade]])
- `POST /api/trade/sleeves` → [[brokerage.sleeves.py]] ([[API trade]])

## Pruebas que lo cubren

- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_overnight_fixes_review.py]]
- [[tests.test_overnight_ui_portfolios_risk.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-10 — NOCHE - IA PAGADA, VOZ ELEVENLABS, PANTALLAS AL TEMA NUEVO (sw v251)]]
- [[Sesión 2026-10-03 (c) — TERMINAL REDISEÑADA + POP-UPS DE COMPRA-VENTA (sw v182)]]
- [[Sesión 2026-07-13 — Etapa O — Khipus Finance AI - 9 frentes + rebrand + Cabina inicial]]
