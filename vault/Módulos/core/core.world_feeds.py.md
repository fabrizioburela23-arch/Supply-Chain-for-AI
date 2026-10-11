---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/world_feeds.py"
lenguaje: "python"
lineas: 632
aliases: ["core/world_feeds.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/world_feeds.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 632 líneas · `core/world_feeds.py`

## Para qué sirve

fuentes OFICIALES nuevas del World Monitor (2026-10-05).

## API pública

- `strait_of(name)` _(línea 94)_
- `shipping_severity(change_pct)` — Caída del tránsito (7 d vs 90 d previos) → 0-100. Subidas = 0. −10 % → 16 · −25 % → 40 · −50 % → 80 · ≤ −62 % → 100. _(línea 132)_
- `parse_portwatch(rows, ref_affected=…)` — rows = [attributes] (varios días × estrechos) → un ítem por estrecho con promedio 7 d, base 90 d previa, cambio % y desglose del último día. _(línea 140)_
- `fetch_shipping(_window)` _(línea 208)_
- `companies_in(text, limit=…)` _(línea 310)_
- `policy_severity(doc_type, text, n_companies, age_days)` — ESTIMACIÓN (palabras clave), no un juicio: base 30; +25 si es Entity List / designación / regla de exportación fuerte; +20 si toca … _(línea 321)_
- `parse_fedreg(payload, now=…)` _(línea 340)_
- `fetch_policy(_window)` _(línea 389)_
- `policy_feed(limit=…)` — Lista COMPLETA (también los documentos sin país identificable) para el panel. _(línea 410)_
- `parse_gdacs(payload)` _(línea 440)_
- `fetch_disasters(_window)` _(línea 479)_
- `parse_advisories(payload)` — [{Title: "Venezuela - Level 4: Do Not Travel", Updated, Published, Link, Summary…}] → ítems de nivel 3-4 (los 1-2 no son alarma). … _(línea 508)_
- `fetch_advisories(_window)` _(línea 547)_
- `parse_outages(payload, now=…)` _(línea 568)_
- `fetch_outages(_window)` _(línea 601)_

**Internas** (empiezan con `_`): `_w`, `_ci`, `_day_of`, `_num`, `_ref_affected`, `_countries_in`, `_company_index`, `_gdacs_ts`

## Depende de

- [[core.country_geo.py]] — importa `lookup`
- [[core.geosit.py]] — importa `CHOKEPOINTS`
- [[core.world.py]] — importa `world`

## Lo usan

- [[core.world.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV CLOUDFLARE_RADAR_TOKEN]]
- [[ENV WORLD_ADVISORIES_URL]]
- [[ENV WORLD_FEDREG_URL]]
- [[ENV WORLD_GDACS_URL]]
- [[ENV WORLD_PORTWATCH_URL]]

## Pruebas que lo cubren

- [[tests.test_world_feeds.py]]
- [[tests.world_feed_fixtures.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (n) — GEOPOLÍTICA CON FUENTES OFICIALES (sw v216)]]
