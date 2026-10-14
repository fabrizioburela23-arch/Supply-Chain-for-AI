---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/instruments.py"
lenguaje: "python"
lineas: 410
aliases: ["core/instruments.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/instruments.py

> Módulo · capa [[Capa Infraestructura]] · 410 líneas · `core/instruments.py`

## Para qué sirve

EMPRESA ≠ INSTRUMENTO (docs/BRECHAS_V2.md L3-13; ARQUITECTURA_V2 §3.2, §17.3, §20.1 #3).

## API pública

- `suffix_of(symbol)` _(línea 64)_
- `exchange_info(symbol)` — (bolsa, moneda, sincroniza_con_NY) para un símbolo de Yahoo; sufijo desconocido → (None, None, True). _(línea 73)_
- `nonsync(symbol)` — ¿Cierra en otro horario que Nueva York? (Asia, Europa, Oceanía, Medio Oriente) → beta de Dimson (L2-M1). _(línea 81)_
- `major_ccy(ccy)` — 'GBp' → ('GBP', 0.01); 'JPY' → ('JPY', 1.0); None/'' → ('USD', 1.0). _(línea 86)_
- `listings_of(node)` — Los listados declarados en la ficha del catálogo (`listings`), normalizados: símbolo de Yahoo en mayúsculas, `is_primary` = coincide con … _(línea 98)_
- `declared_exchange(node, symbol)` — Bolsa de un listado DECLARADO: el MIC manda (OTCM = certificado OTC en EE.UU., no NYSE/Nasdaq); si no, el sufijo de Yahoo. None si la … _(línea 116)_
- `secondary_listings(node)` — Listados declarados que NO son el primario y sí tienen símbolo de Yahoo (los sin símbolo solo se anotan). _(línea 128)_
- `classify(node)` — {kind, review} de una empresa del catálogo (mkt + texto 'ticker'; si declara `listings`, mandan esos). _(línea 133)_
- `local_alternative(node)` — Para un caso de revisión: el símbolo de Yahoo del OTRO listado que declara el texto del catálogo (la acción local, o el listado de origen) … _(línea 160)_
- `from_catalog(nodes)` — Instrumentos primarios (uno por empresa cotizada; el `mkt` de hoy) — dicts listos para insertar. _(línea 187)_
- `secondary_from_catalog(nodes)` — Instrumentos SECUNDARIOS (is_primary False) de las empresas que declaran `listings` — nunca el `mkt`, nunca un símbolo que ya sea primario … _(línea 207)_
- `reference_instruments(currencies=…)` — SPY e ^IRX (referencias del riesgo) + un par {CUR}USD=X por moneda extranjera. _(línea 233)_
- `catalog_nodes()` — Los nodos vigentes por EL accesor único (core/hotviews/hot.graph(): Postgres o, sin base, el snapshot). _(línea 244)_
- `all_instruments(nodes=…)` _(línea 250)_
- `review_list(nodes=…)` — Los casos que Fabrizio debe revisar (BRECHAS #9), en el orden: varios listados, luego OTC/ADR. _(línea 257)_
- `primary_conflicts(session)` — Empresas con MÁS de un instrumento primario en la base (pasa cuando el catálogo cambia de símbolo: la siembra nunca pisa, así que el viejo … _(línea 294)_
- `lot_review_markdown()` — Sección del documento de revisión con los 19 símbolos del lote 2026-10-14 (docs/REVISION_INSTRUMENTOS.md). _(línea 374)_
- `seed(session, nodes=…)` — Inserta los instrumentos que falten (nunca actualiza). Devuelve cuántos insertó. _(línea 400)_

**Internas** (empiezan con `_`): `_recommend`

## Depende de

- [[core.__init__.py]] — importa `hot`
- [[ontology.history_models.py]] — importa `Instrument`

## Lo usan

- [[core.entities.py]] — lo importa
- [[core.import_normalize.py]] — lo importa
- [[core.options.py]] — lo importa
- [[core.prices_api.py]] — lo importa
- [[core.prices_store.py]] — lo importa
- [[core.risk_report.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- [[ontology.company_import.py]] — lo importa
- [[scripts.build_instrument_review.py]] — lo importa
- herramienta MCP `project_portfolio` → [[API herramientas MCP]]

_Además lo importan 5 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_catalog_fix_symbols.py]]
- [[tests.test_instruments.py]]
- [[tests.test_lotek_fixer.py]]
- [[tests.test_prices_eod.py]]
- [[tests.test_risk_on_history.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-14 (c) — LOTE K - IMPORTADOR DE EMPRESAS, PAÍSES ISO-2, CATEGORÍAS, CHAT]]
