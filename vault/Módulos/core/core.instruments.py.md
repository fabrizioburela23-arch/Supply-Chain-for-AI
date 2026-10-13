---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/instruments.py"
lenguaje: "python"
lineas: 213
aliases: ["core/instruments.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/instruments.py

> Módulo · capa [[Capa Infraestructura]] · 213 líneas · `core/instruments.py`

## Para qué sirve

EMPRESA ≠ INSTRUMENTO (docs/BRECHAS_V2.md L3-13; ARQUITECTURA_V2 §3.2, §17.3, §20.1 #3).

## API pública

- `suffix_of(symbol)` _(línea 55)_
- `exchange_info(symbol)` — (bolsa, moneda, sincroniza_con_NY) para un símbolo de Yahoo; sufijo desconocido → (None, None, True). _(línea 64)_
- `nonsync(symbol)` — ¿Cierra en otro horario que Nueva York? (Asia, Europa, Oceanía, Medio Oriente) → beta de Dimson (L2-M1). _(línea 72)_
- `major_ccy(ccy)` — 'GBp' → ('GBP', 0.01); 'JPY' → ('JPY', 1.0); None/'' → ('USD', 1.0). _(línea 77)_
- `classify(node)` — {kind, review} de una empresa del catálogo (mkt + texto 'ticker'). _(línea 86)_
- `local_alternative(node)` — Para un caso de revisión: el símbolo de Yahoo del OTRO listado que declara el texto del catálogo (la acción local, o el listado de origen) … _(línea 106)_
- `from_catalog(nodes)` — Instrumentos primarios (uno por empresa cotizada; el `mkt` de hoy) — dicts listos para insertar. _(línea 130)_
- `reference_instruments(currencies=…)` — SPY e ^IRX (referencias del riesgo) + un par {CUR}USD=X por moneda extranjera. _(línea 146)_
- `catalog_nodes()` — Los nodos vigentes por EL accesor único (core/hotviews/hot.graph(): Postgres o, sin base, el snapshot). _(línea 157)_
- `all_instruments(nodes=…)` _(línea 163)_
- `review_list(nodes=…)` — Los casos que Fabrizio debe revisar (BRECHAS #9), en el orden: varios listados, luego OTC/ADR. _(línea 169)_
- `seed(session, nodes=…)` — Inserta los instrumentos que falten (nunca actualiza). Devuelve cuántos insertó. _(línea 203)_

**Internas** (empiezan con `_`): `_recommend`

## Depende de

- [[core.__init__.py]] — importa `hot`
- [[ontology.history_models.py]] — importa `Instrument`

## Lo usan

- [[core.options.py]] — lo importa
- [[core.prices_api.py]] — lo importa
- [[core.prices_store.py]] — lo importa
- [[core.risk_report.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- [[scripts.build_instrument_review.py]] — lo importa
- herramienta MCP `project_portfolio` → [[API herramientas MCP]]

_Además lo importan 3 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_instruments.py]]
- [[tests.test_prices_eod.py]]
- [[tests.test_risk_on_history.py]]
