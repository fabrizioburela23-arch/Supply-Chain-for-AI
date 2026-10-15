---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/instruments.py"
lenguaje: "python"
lineas: 615
aliases: ["core/instruments.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/instruments.py

> Módulo · capa [[Capa Infraestructura]] · 615 líneas · `core/instruments.py`

## Para qué sirve

EMPRESA ≠ INSTRUMENTO (docs/BRECHAS_V2.md L3-13; ARQUITECTURA_V2 §3.2, §17.3, §20.1 #3).

## API pública

- `suffix_of(symbol)` _(línea 72)_
- `exchange_info(symbol)` — (bolsa, moneda, sincroniza_con_NY) para un símbolo de Yahoo; sufijo desconocido → (None, None, True). _(línea 81)_
- `nonsync(symbol)` — ¿Cierra en otro horario que Nueva York? (Asia, Europa, Oceanía, Medio Oriente) → beta de Dimson (L2-M1). _(línea 89)_
- `major_ccy(ccy)` — 'GBp' → ('GBP', 0.01); 'JPY' → ('JPY', 1.0); None/'' → ('USD', 1.0). _(línea 94)_
- `primary_symbol(node)` — EL símbolo principal de una empresa del grafo: `mkt` (catálogo, o el que escribe el importador = el listado principal); si no hay `mkt`, el … _(línea 108)_
- `listings_of(node)` — Los listados declarados en la ficha del catálogo (`listings`), normalizados: símbolo de Yahoo en mayúsculas, `is_primary` = coincide con el … _(línea 129)_
- `listing_delisted(listing, today=…)` — ¿Listado DADO DE BAJA? — nota «dado de baja» (catálogo, lote 2026-10-14) o `delisted_at` (ficha importada) en una fecha ya pasada; una … _(línea 149)_
- `declared_exchange(node, symbol)` — Bolsa de un listado DECLARADO: el MIC manda (OTCM = certificado OTC en EE.UU., no NYSE/Nasdaq); si no, el sufijo de Yahoo. None si la … _(línea 172)_
- `secondary_listings(node)` — Listados declarados que NO son el primario y sí tienen símbolo de Yahoo (los sin símbolo solo se anotan). _(línea 184)_
- `classify(node)` — {kind, review} de una empresa del catálogo (mkt + texto 'ticker'; si declara `listings`, mandan esos). _(línea 189)_
- `local_alternative(node)` — Para un caso de revisión: el símbolo de Yahoo del OTRO listado que declara el texto del catálogo (la acción local, o el listado de origen) … _(línea 216)_
- `from_catalog(nodes)` — Instrumentos primarios (uno por empresa cotizada; el `mkt` de hoy o, en una empresa importada sin `mkt`, su listado principal) — dicts … _(línea 290)_
- `secondary_from_catalog(nodes)` — Instrumentos SECUNDARIOS (is_primary False) de las empresas que declaran `listings` — nunca el primario, nunca un símbolo que ya sea … _(línea 311)_
- `reference_instruments(currencies=…)` — SPY e ^IRX (referencias del riesgo) + un par {CUR}USD=X por moneda extranjera. _(línea 331)_
- `catalog_nodes()` — Los nodos vigentes por EL accesor único (core/hotviews/hot.graph(): Postgres o, sin base, el snapshot). _(línea 342)_
- `all_instruments(nodes=…)` _(línea 348)_
- `baseline_symbols()` — Símbolos que la app ya seguía ANTES de importar: los del catálogo del repo (data/grafo_v0.json: primarios y listados declarados) + … _(línea 367)_
- `universe(nodes=…, today=…)` — EL universo de cotizaciones del grafo vigente. → { 'primary': [{symbol, company_id, kind, currency, origin, imported, delisted}] (uno por … _(línea 389)_
- `live_symbols(nodes=…, today=…)` — {company_id: símbolo} para lo EN VIVO (capitalización, precio, fundamentales): los primarios vigentes del universo, uno por símbolo, en … _(línea 421)_
- `eod_symbols(nodes=…, today=…)` — Lo que la historia DIARIA baja (core/prices_store): {'equities': [símbolos en orden de prioridad: primarios y luego secundarios, sin los … _(línea 428)_
- `phase_in(symbols, admitted, limit, baseline=…, offset=…)` — Tandas para los símbolos NUEVOS. `symbols` en orden de prioridad (sin repetidos); `admitted` = los nuevos que ya entraron (en memoria, o … _(línea 437)_
- `review_list(nodes=…)` — Los casos que Fabrizio debe revisar (BRECHAS #9), en el orden: varios listados, luego OTC/ADR. _(línea 458)_
- `primary_conflicts(session)` — Empresas con MÁS de un instrumento primario en la base (pasa cuando el catálogo cambia de símbolo: la siembra nunca pisa, así que el viejo … _(línea 499)_
- `lot_review_markdown()` — Sección del documento de revisión con los 19 símbolos del lote 2026-10-14 (docs/REVISION_INSTRUMENTOS.md). _(línea 579)_
- `seed(session, nodes=…)` — Inserta los instrumentos que falten (nunca actualiza). Devuelve cuántos insertó. _(línea 605)_

**Internas** (empiezan con `_`): `_scan`, `_origin_source`, `_recommend`

## Depende de

- [[core.__init__.py]] — importa `_snapshot_parsed`, `hot`
- [[ontology.history_models.py]] — importa `Instrument`

## Lo usan

- [[core.entities.py]] — lo importa
- [[core.import_normalize.py]] — lo importa
- [[core.live_caps.py]] — lo importa
- [[core.options.py]] — lo importa
- [[core.prices_api.py]] — lo importa
- [[core.prices_store.py]] — lo importa
- [[core.risk_report.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- [[ontology.company_import.py]] — lo importa
- [[scripts.build_instrument_review.py]] — lo importa
- herramienta MCP `project_portfolio` → [[API herramientas MCP]]

_Además lo importan 8 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_catalog_fix_symbols.py]]
- [[tests.test_instruments.py]]
- [[tests.test_live_universe.py]]
- [[tests.test_live_universe_db.py]]
- [[tests.test_lotek_fixer.py]]
- [[tests.test_lotel_fixer.py]]
- [[tests.test_prices_eod.py]]
- [[tests.test_risk_on_history.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-14 (c) — LOTE K - IMPORTADOR DE EMPRESAS, PAÍSES ISO-2, CATEGORÍAS, CHAT]]
