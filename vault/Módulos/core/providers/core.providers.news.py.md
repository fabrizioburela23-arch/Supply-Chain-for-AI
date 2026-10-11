---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/providers/news.py"
lenguaje: "python"
lineas: 90
aliases: ["core/providers/news.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/providers/news.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 90 líneas · `core/providers/news.py`

## Para qué sirve

Phase 1 · M3: adapter de noticias.

## API pública

- clase `GdeltProvider` — GDELT: noticias globales y multi-idioma, sin API key. _(línea 36)_
- `news_registry()` _(línea 85)_

**Internas** (empiezan con `_`): `_parse_gdelt_date`

## Depende de

- [[core.http.py]] — importa `_safe_get`
- [[core.providers.base.py]] — importa `NewsProvider`, `ProviderRegistry`, `ProviderStatus`
- [[ontology.provenance.py]] — importa `guess_kind`

## Lo usan

- [[ontology.ingest_news.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_providers.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-22 al 24 — PHASE 1 Live Investment Graph COMPLETA + velocidad + 3D temporal]]
