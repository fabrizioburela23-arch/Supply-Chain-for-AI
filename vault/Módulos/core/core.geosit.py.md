---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/geosit.py"
lenguaje: "python"
lineas: 433
aliases: ["core/geosit.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/geosit.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 433 líneas · `core/geosit.py`

## Para qué sirve

Sala de Situación geopolítica: /api/geo/\*.

## API pública

- `geo_situation()` — La foto completa de la Sala de Situación en UNA llamada (instantánea: las noticias las calienta el hilo de fondo, nunca este request). _(línea 359)_
- `situation_data()` — Datos de /api/geo/situation como dict (lo consume también el World Monitor, core/world.py, para sus capas de chokepoints e inestabilidad). _(línea 376)_

**Internas** (empiezan con `_`): `_gdelt_activity`, `_next_stale`, `_warmer_loop`, `_ensure_warmer`, `_news_for`, `_active_factor_matches`, `_known_ids`, `_score`, `_news_status`

## Depende de

- [[core.world.py]] — importa `err_info`, `gdelt_throttle`, `source_down`, `source_result`
- [[matrix.engine.py]] — importa `active_factors`, `node_index`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`

## Lo usan

- [[core.world.py]] — lo importa
- [[core.world_feeds.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `GET` | `/api/geo/situation` | `geo_situation` | [[core.world.py]] |

Grupos: [[API geo]]

## Pruebas que lo cubren

- [[tests.test_repair_world.py]]
- [[tests.test_world.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (n) — GEOPOLÍTICA CON FUENTES OFICIALES (sw v216)]]
