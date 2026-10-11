---
tipo: "modulo"
capa: "Investigación"
ruta: "research/auto_events.py"
lenguaje: "python"
lineas: 129
aliases: ["research/auto_events.py"]
tags: ["capa/investigacion", "tipo/modulo"]
---

# research/auto_events.py

> Módulo · capa [[Capa Investigación]] · 129 líneas · `research/auto_events.py`

## Para qué sirve

eventos AUTOMÁTICOS del mercado real (Phase 2).

## API pública

- `auto_on()` _(línea 20)_
- `price_anomalies(caps, threshold=…, limit=…)` — [(id, change_pct)] con |cambio| ≥ umbral, mayor movimiento primero. _(línea 24)_
- `dispatch_price_anomalies(caps, execute=…, session_factory=…, today=…)` — Crea (y ejecuta) investigaciones por movimientos anómalos. Devuelve la lista de resultados del router. Nunca lanza. _(línea 42)_
- `fetch_reported_earnings(day_from, day_to, getter=…)` — [{symbol, date, epsActual, epsEstimate, revenueActual, …}] ya REPORTADOS (epsActual presente) en el rango. Sin FINNHUB_KEY → []. _(línea 74)_
- `dispatch_earnings(execute=…, session_factory=…, today=…, getter=…, force=…)` — UNA vez por día: empresas del grafo que reportaron resultados (ayer/hoy) → evento EARNINGS → agentes fundamental/noticias/riesgo, QUICK, … _(línea 87)_

## Depende de

- [[core.ai.py]] — importa `_ai_configured`
- [[core.config.py]] — importa `FINNHUB`
- [[core.entities.py]] — importa `get_index`
- [[core.http.py]] — importa `_safe_get`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[research.router.py]] — importa `dispatch_event`

## Lo usan

- [[core.live_caps.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV RESEARCH_ANOMALY_MAX]]
- [[ENV RESEARCH_ANOMALY_PCT]]
- [[ENV RESEARCH_AUTO_EVENTS]]
- [[ENV RESEARCH_EARNINGS_MAX]]

## Pruebas que lo cubren

- [[tests.test_research.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-29 (noche) — TODO EN VIVO + AUDITORÍA DE DATOS FALSOS (sw v161)]]
