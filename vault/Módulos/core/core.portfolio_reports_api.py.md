---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "core/portfolio_reports_api.py"
lenguaje: "python"
lineas: 468
aliases: ["core/portfolio_reports_api.py"]
tags: ["capa/dinero", "tipo/modulo"]
---

# core/portfolio_reports_api.py

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 468 líneas · `core/portfolio_reports_api.py`

## Para qué sirve

/api/portfolio-report/\* y /api/news/portfolio.

## API pública

- `generate()` _(línea 107)_
- `list_reports()` _(línea 133)_
- `one_report(rid)` _(línea 160)_
- `save_watch()` — Programa (o apaga) los reportes automáticos de UNA cartera. _(línea 182)_
- `list_watches()` _(línea 222)_
- `news_portfolio()` _(línea 240)_
- `ask()` — "Pregúntale a tu cartera": el cerebro de Khipu con tu cartera + tu reporte como contexto. _(línea 257)_
- `user_state()` — GET → {key: {value, updated_at}} · PUT {key, value, updated_at?} (último que escribe gana). _(línea 315)_
- `current_positions(owner, source_key)` — Posiciones ACTUALES de una cartera sincronizada (para los reportes programados): pf:&lt;id> → kh_portfolios · market → eco_pos. None si no hay … _(línea 354)_
- `due(w, now)` _(línea 393)_
- `run_due(now=…, build=…)` — Genera los reportes vencidos (lo llama el hilo; también los tests). _(línea 404)_

**Internas** (empiezan con `_`): `_owner`, `_db`, `_need_owner`, `_no_db`, `_clean_positions`, `_f`, `_title`, `_store`, `_report_notes`, `_ensure_scheduler`, `_boot_scheduler`

## Depende de

- [[core.ai_usage.py]] — importa `ai_context`
- [[core.http.py]] — importa `rate_limit`
- [[core.khipu_chat.py]] — importa `khipu_chat`
- [[core.news_feed.py]] — importa `news_feed`
- [[core.portfolio_report.py]] — importa `portfolio_report`
- [[core.semantic.py]] — importa `_load_snapshot`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[research.models.py]] — importa `PortfolioReport`, `PortfolioWatch`, `UserState`

## Lo usan

- [[research.committee_api.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `POST` | `/api/news/portfolio` | `news_portfolio` | [[engine.app_main.js]], [[engine.brief.js]], [[engine.pfreports.js]], [[engine.temporal-graph.js]] |
| `DELETE,GET` | `/api/portfolio-report/<rid>` | `one_report` | [[engine.pfcommittee.js]], [[engine.pfreports.js]], 2 pruebas |
| `POST` | `/api/portfolio-report/ask` | `ask` | [[engine.pfcommittee.js]], [[engine.pfreports.js]], 2 pruebas |
| `POST` | `/api/portfolio-report/generate` | `generate` | [[engine.pfcommittee.js]], [[engine.pfreports.js]], 2 pruebas |
| `GET` | `/api/portfolio-report/list` | `list_reports` | [[engine.pfcommittee.js]], [[engine.pfreports.js]], 2 pruebas |
| `POST` | `/api/portfolio-report/watch` | `save_watch` | [[engine.pfcommittee.js]], [[engine.pfreports.js]], 2 pruebas |
| `GET` | `/api/portfolio-report/watches` | `list_watches` | [[engine.pfcommittee.js]], [[engine.pfreports.js]], 2 pruebas |
| `GET,PUT` | `/api/user-state` | `user_state` | [[engine.sync.js]], 1 prueba |

Grupos: [[API news]], [[API portfolio-report]], [[API user-state]]

## Pruebas que lo cubren

- [[tests.test_khipus_os_server.py]]
- [[tests.test_portfolio_persist.py]]
- [[tests.test_portfolio_reports.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-03 (g) — SINCRONIZACIÓN ENTRE DISPOSITIVOS (sw v184)]]
- [[Sesión 2026-10-03 (b) — REPORTES DE CARTERA, PREGÚNTALE A TU CARTERA, NOTICIAS DE TU]]
