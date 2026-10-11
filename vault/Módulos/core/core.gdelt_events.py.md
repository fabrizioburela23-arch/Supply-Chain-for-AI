---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/gdelt_events.py"
lenguaje: "python"
lineas: 307
aliases: ["core/gdelt_events.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/gdelt_events.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 307 líneas · `core/gdelt_events.py`

## Para qué sirve

conflicto / protestas / sanciones EN VIVO desde la base de EVENTOS de GDELT 2.0 (archivos crudos cada 15 minutos, públicos y sin clave).

## API pública

- `classify(root, base, n_sources, actor_types=…)` — Código CAMEO (+ tipos de actor) → capa (o None). _(línea 62)_
- `parse_export(text, batch_ts)` — CSV (tab) de 61 columnas → eventos compactos filtrados. _(línea 90)_
- `refresh(now=…, max_new=…)` — Descarga los lotes nuevos (los más recientes primero). Devuelve error o None. _(línea 149)_
- `coverage(window_s, now=…)` — (horas cargadas dentro de la ventana, horas de la ventana). _(línea 237)_
- `aggregate(layer, window_s, severity_fn, now=…, limit=…)` — Eventos de la capa en la ventana → puntos agrupados por lugar (~0,1°). _(línea 244)_
- `severity(articles, sources, days=…)` — 0-100 por COBERTURA (no víctimas): artículos POR DÍA que hablan de ese lugar (+ hasta 3 por fuentes). Calibrado con 24 h reales … _(línea 283)_
- `label_of(code, lang_es=…)` _(línea 303)_

**Internas** (empiezan con `_`): `_base`, `_f`, `_i`, `_ts_of`, `_get`, `_latest`, `_fetch_batch`, `_backfill_on`, `_start_backfill`, `_next_missing`, `_backfill_loop`

## Depende de

_Nada interno._

## Lo usan

- [[core.world.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV WORLD_GDELT_BACKFILL]]
- [[ENV WORLD_GDELT_EVENTS_BASE]]

## Pruebas que lo cubren

- [[tests.test_gdelt_events.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (p) — GEOPOLÍTICA - CAPAS EN PAUSA REVIVIDAS + RIESGO PAÍS + CORTES]]
