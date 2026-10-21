---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/sim_report.py"
lenguaje: "python"
lineas: 206
aliases: ["core/sim_report.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/sim_report.py

> Módulo · capa [[Capa Infraestructura]] · 206 líneas · `core/sim_report.py`

## Para qué sirve

INFORME de la simulación de escenarios (2026-10-21, «que parezca un producto»).

## API pública

- `clean_positions(raw)` — [{id, symbol?, usd}] del navegador → lista validada (máx 60, usd > 0). _(línea 71)_
- `build(sim, lang=…, positions=…, caps=…, caps_as_of=…, snap=…, now=…)` — sim = salida de sim_agents.run → {'rows', 'kpis', 'by_sector', 'by_country', 'portfolio', 'headline', 'method'}. `caps`/`snap` inyectables … _(línea 84)_

**Internas** (empiezan con `_`): `_f`, `_es`, `_caps`, `_snap`, `_sector_label`, `_country_label`, `_kernel_semver`

## Depende de

- [[core.countries.py]] — importa `countries`
- [[core.governance.py]] — importa `governance`
- [[core.live_caps.py]] — importa `get_caps`
- [[core.portfolio_ai.py]] — importa `sector_label`
- [[core.semantic.py]] — importa `semantic`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_sim_report.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
