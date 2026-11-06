---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/price_sim.py"
lenguaje: "python"
lineas: 229
aliases: ["core/price_sim.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/price_sim.py

> Módulo · capa [[Capa Infraestructura]] · 229 líneas · `core/price_sim.py`

## Para qué sirve

«¿ya tocó fondo? ¿hasta dónde puede caer?»: simulación Monte Carlo del PRECIO de una acción.

## API pública

- `earnings_calendar(symbol, getter=…, today=…)` — → (fechas pasadas [(date, hour)], próxima (date, hour) | None, fuente). Finnhub; sin clave → ([], None, None). _(línea 55)_
- `simulate(symbol, prices, earnings=…, today=…, n_paths=…, seed=…, levels=…, fan_days=…)` — `prices` {fecha: cierre ajustado}; `earnings` = (pasadas, próxima, fuente) de earnings_calendar. → dict con todo lo de arriba. Lanza … _(línea 101)_

**Internas** (empiezan con `_`): `_rsi`, `_bdays_between`, `_reaction_moves`

## Depende de

- [[core.config.py]] — importa `FINNHUB`
- [[core.http.py]] — importa `_safe_get`

## Lo usan

- [[mcp_server.ops.py]] — lo importa
- herramienta MCP `simulate_price` → [[API herramientas MCP]]

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_genui_sim_report.py]]
- [[tests.test_price_sim.py]]
