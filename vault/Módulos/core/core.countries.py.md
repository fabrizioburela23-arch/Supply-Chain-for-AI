---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/countries.py"
lenguaje: "python"
lineas: 451
aliases: ["core/countries.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/countries.py

> Módulo · capa [[Capa Infraestructura]] · 451 líneas · `core/countries.py`

## Para qué sirve

UNA tabla de países: ISO-2 ↔ clave del catálogo ↔ nombre ES/EN ↔ región (lote 2026-10-14).

## API pública

- `is_iso2(text)` — ¿Es un código ISO-2 conocido? (solo dos MAYÚSCULAS ASCII: 'CA' sí, 'ca' no — California en un texto de evento). _(línea 341)_
- `iso2_of(text)` — Texto de país (cualquiera de las 136 grafías del catálogo, ISO-2, nombre EN/ES) → ISO-2 o None. 'Europa' / 'RestoEuropa' / 'RestoMundo' → … _(línea 347)_
- `region_of(text)` — 'Europa' | 'RestoEuropa' | 'RestoMundo' cuando el texto NO nombra un país real; None si sí lo nombra. _(línea 373)_
- `catalog_key_of(iso2)` — ISO-2 → clave del catálogo de HOY ('US' → 'EEUU', 'GB' → 'ReinoUnido'); sin clave → nombre en inglés; código desconocido → el mismo texto. _(línea 387)_
- `label(code, lang=…)` — Nombre legible: label('US','es') → 'Estados Unidos'. Acepta ISO-2, una región o una clave del catálogo. _(línea 395)_
- `is_europe(text)` — ¿El país (ISO-2, clave o texto) está en Europa? Las regiones 'Europa'/'RestoEuropa' también. _(línea 409)_
- `iso2_of_props(props)` — ISO-2 de las propiedades de un objeto: `hq_country` (ISO del importador) > `country_iso2` > `country` > `loc` cuando `country` es una … _(línea 417)_
- `resolve(text)` — Todo junto: {'iso2', 'key', 'region', 'es', 'en'} (key = clave del catálogo de hoy o None). _(línea 434)_
- `js_table()` — La tabla para la gemela JS (engine/geo_coords.js), en JSON determinista. _(línea 446)_

**Internas** (empiezan con `_`): `_norm`, `_name_index`

## Depende de

- [[core.world.py]] — importa `_js_norm`, `country_key`

## Lo usan

- [[core.context_engine.py]] — lo importa
- [[core.import_normalize.py]] — lo importa
- [[core.sim_report.py]] — lo importa
- [[core.world.py]] — lo importa
- [[mcp_server.ops.py]] — lo importa
- [[scripts.build_country_review.py]] — lo importa
- herramienta MCP `rank_by_market` → [[API herramientas MCP]]

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_countries.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-14 (c) — LOTE K - IMPORTADOR DE EMPRESAS, PAÍSES ISO-2, CATEGORÍAS, CHAT]]
