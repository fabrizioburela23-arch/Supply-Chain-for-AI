---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "engine/pfreports.js"
lenguaje: "javascript"
lineas: 414
aliases: ["engine/pfreports.js"]
tags: ["capa/dinero", "tipo/modulo"]
---

# engine/pfreports.js

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 414 líneas · `engine/pfreports.js`

## Para qué sirve

📄 REPORTES · 📰 NOTICIAS · 💬 PREGÚNTALE A TU CARTERA (secciones de Comité → 💼 Mi cartera; las monta engine/pfcommittee.js)

## API pública (globales que define)

`window.KhipuPortfolioExtras`

## Depende de

- [[app.html]] — usa `safeUrl`
- [[engine.app_main.js]] — usa `BASE`, `LANG`
- [[engine.committee.js]] — usa `KhipuCommittee`
- [[engine.mascot.js]] — usa `KhipuMascot`
- [[engine.toast.js]] — usa `KhipuToast`, `khipuActor`

Se carga en [[app.html]] en la posición **62 de 99** (línea 3170), después de [[engine.pfcommittee.js]] y antes de [[engine.sync.js]].

## Lo usan

- [[app.html]] — lo carga con `<script>` (posición 62)
- [[engine.pfcommittee.js]] — usa `KhipuPortfolioExtras`

## Endpoints que llama

- `DELETE,GET /api/portfolio-report/<rid>` → [[core.portfolio_reports_api.py]] ([[API portfolio-report]])
- `GET /api/news/<ticker>` → [[server.py]] ([[API news]])
- `GET /api/portfolio-report/list` → [[core.portfolio_reports_api.py]] ([[API portfolio-report]])
- `GET /api/portfolio-report/watches` → [[core.portfolio_reports_api.py]] ([[API portfolio-report]])
- `POST /api/news/portfolio` → [[core.portfolio_reports_api.py]] ([[API news]])
- `POST /api/portfolio-report/ask` → [[core.portfolio_reports_api.py]] ([[API portfolio-report]])
- `POST /api/portfolio-report/generate` → [[core.portfolio_reports_api.py]] ([[API portfolio-report]])
- `POST /api/portfolio-report/watch` → [[core.portfolio_reports_api.py]] ([[API portfolio-report]])

## Pruebas que lo cubren

- [[tests.test_cleanup_dialogs.py]]
- [[tests.test_committee_os_pf_tokens.py]]
- [[tests.test_committee_os_ui.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-09 — EL COMITÉ ENTRA A KHIPUS OS (sw v250)]]
- [[Sesión 2026-10-03 (b) — REPORTES DE CARTERA, PREGÚNTALE A TU CARTERA, NOTICIAS DE TU]]
