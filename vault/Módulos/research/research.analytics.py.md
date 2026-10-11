---
tipo: "modulo"
capa: "Investigación"
ruta: "research/analytics.py"
lenguaje: "python"
lineas: 266
aliases: ["research/analytics.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/analytics.py

> Módulo · capa [[Capa Investigación]] · 266 líneas · `research/analytics.py`

## Para qué sirve

ANÁLISIS CUANTITATIVO determinista para los agentes.

## API pública

- `fundamental_ratios(fin, profile=…)` — fin: get_annual_financials() (USD). profile: get_live_profile() o None. _(línea 55)_
- `technical_indicators(series, bench=…)` — series/bench: [(ts, close)] diarios (~1 año). Devuelve (dict, texto). _(línea 163)_
- `peer_table(entity_label, entity_profile, peers)` — peers: [(label, profile)]. Devuelve (dict, texto) o (None, '') con < 2 pares. _(línea 233)_

**Internas** (empiezan con `_`): `_f`, `_pct`, `_b`, `_series`, `_last_two`, `_sma`, `_rsi`, `_ret`, `_median`, `_as_pct`

## Depende de

_Nada interno._

## Lo usan

- [[research.context.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_analytics.py]]
- [[tests.test_cleanup_server.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-02 (noche) — ANÁLISIS MÁS PROFUNDO + CONCLUSIONES EN TODAS PARTES (sw v179)]]
