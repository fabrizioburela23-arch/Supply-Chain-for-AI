---
tipo: "modulo"
capa: "Datos en vivo (cotizaciones, mundo, espacio, fundamentales)"
ruta: "core/live_fundamentals.py"
lenguaje: "python"
lineas: 121
aliases: ["core/live_fundamentals.py"]
tags: ["capa/datos-vivo", "tipo/modulo"]
---

# core/live_fundamentals.py

> Módulo · capa [[Capa Datos en vivo (cotizaciones, mundo, espacio, fundamentales)]] · 121 líneas · `core/live_fundamentals.py`

## Para qué sirve

FUNDAMENTALES EN VIVO de TODAS las cotizadas del grafo.

## API pública

- `refresh(profile_fn=…, now=…, n=…)` — Una tanda (bloqueante; el reloj del servidor la llama). Devuelve un resumen. Sin `n`: BATCH, o BATCH×CATCHUP mientras haya empresas nunca … _(línea 47)_
- `get_all()` — {fund: {node_id: {operating_margin, revenue_growth_q, …, source, as_of}}, n, universe, last_run}. _(línea 97)_
- `live_margin(nid)` — Margen operativo REAL (fracción) de una empresa, o None si aún no hay dato en vivo. _(línea 106)_
- `version()` — Contador de tandas terminadas: la tarjeta V3 (core/hotviews/views/card.py) recalcula el vector NRS solo cuando cambia (el margen en vivo … _(línea 117)_

**Internas** (empiezan con `_`): `_universe`, `_pick`

## Depende de

- [[core.company_data.py]] — importa `get_live_profile`
- [[core.live_caps.py]] — importa `_symbols_by_id`

## Lo usan

- [[core.world.py]] — lo importa
- [[research.agent_skills.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 8 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_cleanup_nrs_parity.py]]
- [[tests.test_governance_seed_parity.py]]
- [[tests.test_hot_invalidation.py]]
- [[tests.test_hot_views_parity.py]]
- [[tests.test_live_fundamentals.py]]
- [[tests.test_lotej_review_fixes.py]]
- [[tests.test_scale_tensor_5k.py]]
- [[tests.test_scale_tensor_derived.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-05 (dd) — RENDIMIENTO DE MI CARTERA COMO GRÁFICO SIN IA (sw v238-v239)]]
- [[Sesión 2026-10-05 (aa) — FUNDAMENTALES EN VIVO DE TODO EL GRAFO (sw v234)]]
