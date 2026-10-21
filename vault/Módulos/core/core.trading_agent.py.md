---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "core/trading_agent.py"
lenguaje: "python"
lineas: 1170
aliases: ["core/trading_agent.py"]
tags: ["capa/dinero", "tipo/modulo"]
---

# core/trading_agent.py

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 1.170 líneas · `core/trading_agent.py`

## Para qué sirve

Agente de trading de la cuenta de la casa — /api/trade/agent/\* (G5-05, lote I4: salió de server.py SIN cambiar comportamiento).

## API pública

- `bind(host)` — server.py se pasa a sí mismo: la config y los ayudantes de la cuenta de la casa se leen de ahí en cada llamada. _(línea 30)_
- `agent_start()` _(línea 961)_
- `agent_stop()` _(línea 999)_
- `agent_status()` _(línea 1011)_
- `agent_config()` _(línea 1042)_
- `agent_signals()` _(línea 1065)_
- `agent_signal_take(sid)` — La persona aprueba la señal (su PIN = su confirmación): misma validación que /api/trade/order y EL camino único. 409 si venció, ya se usó o … _(línea 1079)_
- `agent_signal_dismiss(sid)` — Descartar una señal: queda en el libro (trade.agent_signal, status noop) quién la descartó. _(línea 1150)_

**Internas** (empiezan con `_`): `_AgentOrderError`, `_agent_log`, `_agent_universe`, `_agent_parse`, `_agent_config_view`, `_auto_live_refused`, `_agent_exec_block`, `_agent_analyze`, `_agent_clean_analysis`, `_agent_get_positions`, `_agent_open_order_symbols`, `_agent_get_account`, `_alpaca_tradable`, `_agent_board_by_symbol`, `_agent_context`, `_agent_guard`, `_agent_tone`, `_signals_prune`, `_signal_add`, `_signals_view`, `_agent_principal`, `_agent_signal_ctx`, `_agent_record_signal`, `_agent_order`, `_agent_place`, `_agent_stop_losses`, `_agent_stop_signals`, `_agent_run_cycle`, `_agent_thread_fn`, `_agent_persist`, `_agent_restore`, `_signal_get`

## Depende de

- [[brokerage.service.py]] — importa `crypto_pair`, `service`
- [[core.decisions.py]] — importa `decisions`
- [[core.http.py]] — importa `rate_limit`
- [[core.identity.py]] — importa `identity`
- [[core.pin.py]] — importa `require_pin`
- [[core.quotes.py]] — importa `fetch_quotes_live`
- [[core.risk_report.py]] — importa `fetch_history`
- [[core.semantic.py]] — importa `_load_snapshot`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[research.analytics.py]] — importa `technical_indicators`
- [[research.committee.py]] — importa `board`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `POST` | `/api/trade/agent/config` | `agent_config` | [[engine.signals.js]], 2 pruebas |
| `GET` | `/api/trade/agent/signals` | `agent_signals` | [[engine.signals.js]], 1 prueba |
| `POST` | `/api/trade/agent/signals/<sid>/dismiss` | `agent_signal_dismiss` | [[engine.signals.js]], 1 prueba |
| `POST` | `/api/trade/agent/signals/<sid>/take` | `agent_signal_take` | [[engine.signals.js]], 2 pruebas |
| `POST` | `/api/trade/agent/start` | `agent_start` | [[engine.app_trade_panel.js]], [[engine.signals.js]], 3 pruebas |
| `GET` | `/api/trade/agent/status` | `agent_status` | [[engine.app_trade_panel.js]], [[engine.signals.js]], 3 pruebas |
| `POST` | `/api/trade/agent/stop` | `agent_stop` | [[engine.app_trade_panel.js]], [[engine.signals.js]], 2 pruebas |

Grupos: [[API trade]]

## Pruebas que lo cubren

- [[tests.test_agent_signals_one_tap.py]]
- [[tests.test_security.py]]
- [[tests.test_trading_agent_ledger.py]]
- [[tests.test_voice_agent_split.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
- [[Sesión 2026-10-13 (k) — FASE 2+ LOTE I - rutas con decisión, CSP estricta, riesgo]]
