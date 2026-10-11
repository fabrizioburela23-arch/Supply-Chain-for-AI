---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/space.py"
lenguaje: "python"
lineas: 640
aliases: ["core/space.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/space.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 640 líneas · `core/space.py`

## Para qué sirve

SPACE MONITOR (pestaña 🚀 Espacio): /api/space2/\*.

## API pública

- `err_info(err)` — Código de error → {error_code, error_es, error_en, error} (bilingüe). _(línea 144)_
- `resolve_org(name, abbrev=…)` — Resuelve un nombre de organización de LL2 al grafo. Intenta: nombre completo · abreviatura (solo coincidencia exacta de id/label/alias: una … _(línea 191)_
- `match_graph(provider, agencies, mission_name, launch_name, manufacturer=…)` — Empresas del grafo implicadas en un lanzamiento. provider/manufacturer: {'name','abbrev'} · agencies: [{'name','abbrev'}]. _(línea 226)_
- `normalize_launch(raw, match=…)` — Lanzamiento LL2 → forma estable del Space Monitor. None si no es válido. _(línea 317)_
- `normalize_payload(payload, match=…)` — Respuesta LL2 ({results:[…]}) → lista normalizada. Lanza ValueError si el formato no es el esperado. _(línea 374)_
- `ll2_base()` _(línea 406)_
- `get_launches(window)` — Lanzamientos de la ventana (caché) + estado honesto de la fuente. _(línea 454)_
- `next_launch(upcoming, now=…)` _(línea 521)_
- `summarize(upcoming, previous, now=…)` _(línea 532)_
- `api_space2_launches()` — GET /api/space2/launches?window=upcoming|previous&limit=30 _(línea 611)_
- `api_space2_summary()` — GET /api/space2/summary — próximo lanzamiento, conteos por semana/mes y proveedor, plataformas activas y empresas del grafo implicadas. _(línea 633)_

**Internas** (empiezan con `_`): `_now`, `_iso`, `_parse_iso`, `_safe_url`, `_float`, `_valid_ll`, `_txt`, `_graph_by_id`, `_resolve`, `_status`, `_org`, `_vids`, `_infos`, `_reset_cache`, `_budget_ok`, `_http_get_json`, `_fetch`, `_provider_name`, `_count_by_provider`, `_bad`

## Depende de

- [[core.entities.py]] — importa `UMBRAL_BUSQUEDA`, `resolve`
- [[core.http.py]] — importa `rate_limit`
- [[core.world.py]] — importa `_graph`, `err_info`

## Lo usan

- [[core.khipu_chat.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/space2/launches` | `api_space2_launches` | [[engine.spacemonitor.js]], 1 prueba |
| `GET` | `/api/space2/summary` | `api_space2_summary` | [[engine.spacemonitor.js]], 1 prueba |

Grupos: [[API space2]]

## Variables de entorno que lee (solo nombres)

- [[ENV SPACE_LL2_BASE]]

## Pruebas que lo cubren

- [[tests.test_space2.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-30 al 10-02 — MONITORES, RIESGO FÁCIL, ASISTENTE, CEREBRO DE KHIPU]]
