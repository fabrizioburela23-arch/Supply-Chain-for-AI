---
tipo: "modulo"
capa: "Comité"
ruta: "engine/pfcommittee.js"
lenguaje: "javascript"
lineas: 550
aliases: ["engine/pfcommittee.js"]
tags: ["capa/comite", "tipo/modulo"]
---

# engine/pfcommittee.js

> Módulo · capa [[Capa Comité]] · 550 líneas · `engine/pfcommittee.js`

## Para qué sirve

💼 COMITÉ DE CARTERA (pestaña "Mi cartera" del Comité)

## API pública (globales que define)

`window.KhipuPortfolioCommittee`, `window.KhipuProfile`

## Depende de

- [[app.html]] — usa `BASE`, `LANG`, `MKT`, `NODE_BY_ID`, `_tradeFetch`
- [[engine.committee.js]] — usa `KhipuCommittee`
- [[engine.explain.js]] — usa `explainMetric`
- [[engine.mascot.js]] — usa `KhipuMascot`
- [[engine.pfreports.js]] — usa `KhipuPortfolioExtras`
- [[engine.portfolios.js]] — usa `KhipuPortfolios`
- [[engine.resolve.js]] — usa `_surface`
- [[engine.sync.js]] — usa `KhipuSync`
- [[engine.toast.js]] — usa `KhipuToast`, `khipuActor`

Se carga en [[app.html]] en la posición **58 de 92** (línea 7902), después de [[engine.aispend.js]] y antes de [[engine.pfreports.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 58)
- [[engine.committee.js]] — usa `KhipuPortfolioCommittee`
- [[engine.khipu_chat.js]] — usa `KhipuPortfolioCommittee`, `KhipuProfile`
- [[engine.localcharts.js]] — usa `KhipuPortfolioCommittee`

## Endpoints que llama

- `DELETE,GET /api/portfolio-report/<rid>` → [[core.portfolio_reports_api.py]] ([[API portfolio-report]])
- `GET /api/portfolio-report/list` → [[core.portfolio_reports_api.py]] ([[API portfolio-report]])
- `GET /api/portfolio-report/watches` → [[core.portfolio_reports_api.py]] ([[API portfolio-report]])
- `GET /api/trade/positions/detail` → [[server.py]] ([[API trade]])
- `POST /api/committee/portfolio` → [[research.committee_api.py]] ([[API committee]])
- `POST /api/portfolio-report/ask` → [[core.portfolio_reports_api.py]] ([[API portfolio-report]])
- `POST /api/portfolio-report/generate` → [[core.portfolio_reports_api.py]] ([[API portfolio-report]])
- `POST /api/portfolio-report/watch` → [[core.portfolio_reports_api.py]] ([[API portfolio-report]])
- `POST /api/research/jobs` → [[research.api.py]] ([[API research]])

## Pruebas que lo cubren

- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_committee_os_pf_apply.py]]
- [[tests.test_committee_os_pf_tokens.py]]
- [[tests.test_committee_os_ui.py]]
- [[tests.test_portfolio_persist.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-09 — EL COMITÉ ENTRA A KHIPUS OS (sw v250)]]
- [[Sesión 2026-10-05 (q) — COMITÉ DE CARTERA GEOPOLÍTICA EN VIVO (sw v223)]]
- [[Sesión 2026-10-05 (m) — EL COMITÉ ANALIZA TODAS LAS POSICIONES (sw v215)]]
- [[Sesión 2026-10-03 — GASTO DE IA, SIM. ESTRUCTURAL, AVATARES, CANVAS, COMITÉ DE CARTERA]]
