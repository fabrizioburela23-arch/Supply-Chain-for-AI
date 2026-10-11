---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/providers/base.py"
lenguaje: "python"
lineas: 201
aliases: ["core/providers/base.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/providers/base.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 201 líneas · `core/providers/base.py`

## Para qué sirve

Phase 1 · M3: el contrato de los proveedores.

## API pública

- clase `ProviderStatus` — Si un proveedor puede usarse, y si no, POR QUÉ. 'Sin configurar' y 'falló' son cosas distintas y la UI debe poder distinguirlas. _(línea 41)_
- `make_quote(symbol, price, prev_close=…, provider=…, currency=…, converted=…, volume=…, as_of=…, delayed_minutes=…)` — Esquema ÚNICO de cotización. Todo el sistema consume esto, nunca el JSON crudo de un proveedor. _(línea 61)_
- clase `MarketDataProvider` — Contrato de datos de mercado. Un adapter nuevo = implementar esto; ni las rutas ni la UI cambian. _(línea 116)_
- clase `NewsProvider` — Contrato de noticias. Lo consume M4 (ingesta al grafo). _(línea 141)_
- clase `ProviderRegistry` — Cascada de proveedores: se prueban en orden y responde el primero que tiene el dato. La respuesta dice SIEMPRE quién contestó (`provider`), … _(línea 162)_

**Internas** (empiezan con `_`): `_utcnow`, `_iso`

## Depende de

_Nada interno._

## Lo usan

- [[core.providers.market.py]] — lo importa
- [[core.providers.news.py]] — lo importa

_Además lo importan 4 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_graph_api.py]]
- [[tests.test_ingest_news.py]]
- [[tests.test_providers.py]]
- [[tests.test_quotes_live.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-22 al 24 — PHASE 1 Live Investment Graph COMPLETA + velocidad + 3D temporal]]
