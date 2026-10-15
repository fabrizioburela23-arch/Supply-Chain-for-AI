---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/import_normalize.py"
lenguaje: "python"
lineas: 807
aliases: ["core/import_normalize.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/import_normalize.py

> Módulo · capa [[Capa Infraestructura]] · 807 líneas · `core/import_normalize.py`

## Para qué sirve

normalización de la ficha khipus.company/1 a la convención interna (E2.2).

## API pública

- `iso2_of(text)` — Cualquier grafía del catálogo, ISO-2 o nombre ES/EN → ISO-2. 'Europa'/'RestoMundo' → None. _(línea 67)_
- `region_of(text)` — 'Europa' | 'RestoEuropa' | 'RestoMundo' | None (cuando el texto no es un país real). _(línea 97)_
- `catalog_key_of(iso2)` — ISO-2 → clave del catálogo de hoy ('US' → 'EEUU'); desconocido → nombre en inglés. _(línea 113)_
- `country_label(iso2, lang=…)` _(línea 122)_
- `suffix_of_mic(mic)` — MIC → sufijo de Yahoo ('XSHE' → 'SZ'; EE.UU. → ''); desconocido → None. _(línea 150)_
- `exchange_label(mic)` — Nombre de la bolsa como lo conoce core/instruments (por el sufijo); sin dato → el MIC. _(línea 155)_
- `yahoo_symbol_for(ticker, mic)` — Símbolo de Yahoo esperado para (ticker, MIC): 'TSM'+'XNYS' → 'TSM'; '2330'+'XTAI' → '2330.TW'. Yahoo escribe el punto de las clases como … _(línea 168)_
- `yahoo_matches_mic(yahoo_symbol, mic)` — ¿El sufijo del símbolo de Yahoo corresponde al MIC declarado? None si el MIC es desconocido. _(línea 180)_
- `currency_of_mic(mic)` — Moneda en que Yahoo da el precio para esa bolsa (core/instruments.SUFFIX o MIC_CURRENCY); None si no se sabe. Subunidades (GBp, ZAc, ILA) … _(línea 201)_
- `partial_date(text, wide=…)` — '2021' | '2021-07' | '2021-07-15' → (inicio, fin_exclusivo, precisión) en UTC. El día nunca se inventa: la precisión dice cuánto se sabe … _(línea 225)_
- `valid_from_of(start_text)` — `start` de un vínculo → (valid_from ISO, valid_from_known). Sin start → el centinela GENESIS (2000-01-01, "desde que se rastrea") con … _(línea 253)_
- `valid_to_of(end_text)` — `end` → valid_to = primer instante DESPUÉS del período conocido ('2021-07' → 2021-08-01). None sin end. _(línea 263)_
- `money(fact)` — f_money → {value (unidades), currency, period, as_of, source_url, confidence}. La conversión a USD la hace el servidor con fx_daily del … _(línea 273)_
- `pct(value)` — Porcentaje 0-100 de la ficha → fracción 0-1 que usa el catálogo (margin). None si no es número. _(línea 289)_
- `ascii_fold(s)` _(línea 301)_
- `khipus_id_from(name)` — 'LG Energy Solution' → 'LGEnergySolution'; '3M' → 'Co3M'; 'Ørsted' → 'Orsted' (Ø/Æ/ß/Ł no se descomponen con NFKD: tabla propia); '宁德时代' → … _(línea 310)_
- `is_khipus_id(s)` _(línea 327)_
- `encode_url(url)` — Repara el FORMATO de un enlace: quita espacios de los extremos y codifica los espacios internos y los corchetes de la ruta/consulta (%20, … _(línea 393)_
- `sanitize_record(rec)` — Ficha (dict) → (ficha_saneada, registro). PURA (copia profunda; la entrada no se toca), DETERMINISTA e IDEMPOTENTE (sanitize(sanitize(x)) … _(línea 766)_
- `sanitize_summary(logs)` — {regla: n} de uno o varios registros (lista de entradas o lista de listas). _(línea 800)_

**Internas** (empiezan con `_`): `_countries_mod`, `_p_key`, `_p_idx`, `_log`, `_fiscal_year_of`, `_period_fixed`, `_ticker_fixed`, `_suffix_mics`, `_yahoo_suffix`, `_currency_of_suffix`, `_declared_tickers`, `_sanitize_listing`, `_sanitize_counterparty`, `_repair`, `_field_info`, `_inner_model`, `_drop_target`, `_orig_paths`, `_drop_order_key`, `_drop_invalid`

## Depende de

- [[core.countries.py]] — importa `countries`
- [[core.instruments.py]] — importa `MINOR_UNITS`, `SUFFIX`
- [[core.world.py]] — importa `world`
- [[ontology.company_import.py]] — importa `MIC_COUNTRY`, `_listing_kind`
- [[ontology.company_schema.py]] — importa `CompanyRecord`, `FORBIDDEN_KEYS`
- [[ontology.service.py]] — importa `GENESIS_SENTINEL`

## Lo usan

- [[core.entities.py]] — lo importa
- [[ontology.company_import.py]] — lo importa

_Además lo importan 4 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_import_normalize.py]]
- [[tests.test_import_sanitize.py]]
- [[tests.test_lotek_fixer.py]]
- [[tests.test_lotel_fixer.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-14 (c) — LOTE K - IMPORTADOR DE EMPRESAS, PAÍSES ISO-2, CATEGORÍAS, CHAT]]
