---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/sleeve_agents.py"
lenguaje: "python"
lineas: 266
aliases: ["core/sleeve_agents.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/sleeve_agents.py

> Módulo · capa [[Capa Infraestructura]] · 266 líneas · `core/sleeve_agents.py`

## Para qué sirve

UN AGENTE POR CARTERA (docs/CARTERAS_Y_AGENTES.md fase 3, 2026-11-19).

## API pública

- `clean_config(raw, safe_ticker=…)` — dict cualquiera → configuración acotada + avisos. Nunca lanza. _(línea 40)_
- `parse_text(text, lang=…)` — Texto en palabras → (config, resumen, avisos). La IA solo PROPONE; nada se guarda aquí. _(línea 82)_
- `describe(cfg, lang=…)` — Resumen legible (sin IA) de una configuración. _(línea 101)_
- `run_due(now=…)` — Corre los agentes de cartera vencidos. → nº de carteras revisadas. Nunca lanza. _(línea 127)_
- `run_one(sleeve_id, name, cfg)` — Un ciclo del agente de UNA cartera. _(línea 170)_

**Internas** (empiezan con `_`): `_num`, `_due`, `_log`, `_price`

## Depende de

- [[brokerage.models.py]] — importa `BrokerSleeve`
- [[brokerage.service.py]] — importa `service`
- [[brokerage.sleeves.py]] — importa `sleeves`
- [[core.ai.py]] — importa `ai`
- [[core.http.py]] — importa `_safe_ticker`
- [[core.quotes.py]] — importa `fetch_quotes_live`
- [[core.trading_agent.py]] — importa `trading_agent`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`

## Lo usan

- [[brokerage.sleeves.py]] — lo importa
- [[core.trading_agent.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_order_single_path.py]]
- [[tests.test_sleeve_agents.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
