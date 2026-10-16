---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "brokerage/service.py"
lenguaje: "python"
lineas: 2340
aliases: ["brokerage/service.py"]
tags: ["capa/dinero", "tipo/modulo"]
---

# brokerage/service.py

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 2.340 líneas · `brokerage/service.py`

## Para qué sirve

lógica del corretaje multi-cliente (CONTRATO COMPARTIDO).

## API pública

- `available()` — ¿Se puede usar el corretaje? (requiere la base de la ontología). _(línea 85)_
- `approval_ttl_s()` — Cuánto espera una orden en la cola de aprobación: policy.broker_risk.approval_ttl_min (D2, cierre del lote H, E5). … _(línea 145)_
- `audit(session, actor, action, client_id=…, order_id=…, detail=…)` — APPEND-ONLY. Jamás se escribe un secreto en `detail`. Desde el paso 5 cada fila lleva `detail._who` (principal autenticado + canal) aunque … _(línea 176)_
- `list_audit(session, client_id=…, limit=…)` _(línea 191)_
- `account_fingerprint(rec)` — Huella de la cuenta REAL detrás del cliente (modo + URL + credenciales). Se guarda en cada previsualización: si cambia antes de ejecutar … _(línea 209)_
- `client_dict(rec)` — Vista pública del cliente — SIN secretos (solo el hint enmascarado). _(línea 223)_
- `ensure_house_client(session)` — Registra la cuenta de la casa (ALPACA_KEY/SECRET/BASE) como cliente «Cuenta principal» si hay credenciales en el entorno. Idempotente y a … _(línea 273)_
- `list_clients(session)` _(línea 318)_
- `get_client(session, client_id)` _(línea 350)_
- `create_client(session, name, email=…, notes=…, mode=…, risk_profile=…, limits=…, mandate=…, actor=…)` _(línea 391)_
- `update_client(session, client_id, patch, actor=…)` _(línea 455)_
- `pause_client(session, client_id, actor=…)` _(línea 536)_
- `resume_client(session, client_id, actor=…)` _(línea 540)_
- `make_alpaca(rec)` — AlpacaClient para el cliente (los tests lo sustituyen por uno falso). _(línea 547)_
- `set_credentials(session, client_id, api_key, api_secret, env=…, actor=…, verify=…)` _(línea 589)_
- `account_snapshot(session, client_id)` _(línea 677)_
- `reference_price(alp, symbol, positions)` — (precio, fuente) de MERCADO para estimar montos — nunca inventado: posición en Alpaca → último trade de Alpaca → Finnhub. (None, None) si … _(línea 700)_
- `market_clock(alp)` _(línea 727)_
- `daily_used(session, client_id)` — Público (lo lee el comité): US\$ comprados hoy por el cliente. _(línea 750)_
- `order_dict(row, client_name=…)` _(línea 948)_
- `checks_report(checks, focus_id, ev=…, policy_mode=…)` — run_checks → el veredicto que RIGE, en la forma de DecisionCtx.gate (decision_violations). Los controles en sombra y los avisos quedan como … _(línea 1047)_
- `order_gate(rec, spec, ev, order_id, source, channel=…, channel_proof=…, policy_changed=…, acc=…, ctx=…)` — Puerta G3 (order.ttl) en SOMBRA: hechos de run_checks + reglas nuevas → GateReport/1 adjunto a la decisión. Nunca bloquea ni lanza (paso … _(línea 1092)_
- `preview_order(session, client_id, symbol, side, notional=…, qty=…, order_type=…, limit_price=…, source=…, requested_by=…, proposal_id=…, rationale=…, client_order_id=…, time_in_force=…, channel=…, channel_proof=…, checks_mode=…, parent_decision_id=…, reuse_eval=…)` _(línea 1244)_
- `send_trace_begin()` — Empieza a anotar (en ESTE hilo) los client_order_id que llegan a tocar Alpaca. Lo usan quienes envuelven house_order/house_close en su … _(línea 1406)_
- `send_trace()` — Los client_order_id enviados a Alpaca desde send_trace_begin() en este hilo (lista vacía si ninguno). _(línea 1414)_
- `record_unknown_after_send(coids, actor, error_name, source=…, client_id=…)` — Rastro DURABLE (sesión propia, append-only) de una orden que salió hacia Alpaca pero cuya transacción se revirtió: el reintento con el … _(línea 1419)_
- `confirm_order(session, preview_id, approved_by, source=…, channel_proof=…)` _(línea 1694)_
- `approve_preview(session, preview_id, approved_by)` — Aprobación HUMANA (la ruta exige PIN) de una propuesta de MCP/comité/agente. _(línea 1758)_
- `reject_preview(session, preview_id, actor, reason=…)` _(línea 1779)_
- `pending_approvals(session)` _(línea 1804)_
- `list_orders(session, client_id=…, status=…, limit=…)` _(línea 1845)_
- `get_order(session, order_id)` _(línea 1858)_
- `cancel_order(session, order_id, actor)` — Cancela (antes o después de enviarla) y deja la decisión order.cancel (hija de order.submit si la hay). _(línea 1905)_
- `sync_orders(session, client_id=…, actor=…)` — Actualiza desde Alpaca el estado de las órdenes abiertas, y reconcilia por client_order_id las que quedaron con estado desconocido (sin id … _(línea 1970)_
- `poll_fills_job()` — Tarea del reloj (core/scheduler, system:broker_fills): si hay órdenes abiertas, las sincroniza con Alpaca → broker_fills + … _(línea 2017)_
- `house_order(session, symbol, side, notional=…, qty=…, order_type=…, limit_price=…, time_in_force=…, client_order_id=…, source=…, channel=…, requested_by=…, rationale=…, channel_proof=…, checks_mode=…, parent_decision_id=…)` — UNA orden de la cuenta de la casa = preview_order(HOUSE_ID) + confirm_order en la misma llamada (la persona ya confirmó en el diálogo de la … _(línea 2067)_
- `house_close(session, symbol, client_order_id=…, channel=…, requested_by=…, source=…)` — Cerrar UNA posición completa (1-clic «CLOSE») = orden de mercado por TODA la cantidad que hay (venta si es larga, compra si es corta) por … _(línea 2175)_
- `crypto_pair(sym)` — 'BTCUSD' (símbolo de posición de Alpaca) → 'BTC/USD' (símbolo de orden). _(línea 2207)_
- `oauth_start(session, client_id, env=…, actor=…)` _(línea 2219)_
- `oauth_callback(session, state, code, error=…)` — Valida el `state` (firmado, de un solo uso, < 15 min), canjea el código y guarda el token CIFRADO. Devuelve {ok, client_id, client_name, … _(línea 2246)_
- `public_status()` — Lo único que se muestra SIN PIN. _(línea 2305)_
- `status_info()` — Detalle de configuración (va detrás del PIN: revela la postura de seguridad). _(línea 2310)_

**Internas** (empiezan con `_`): `_now`, `_iso`, `_f`, `_aware`, `_err`, `_not_found`, `_Bad`, `_sha`, `_who`, `_connected`, `_expire_open`, `_account_changed`, `_lookup`, `_client_rec`, `_name_taken`, `_clean_limits`, `_clean_mandate`, `_policy_snapshot`, `_policy_change`, `_account_decision`, `_valid_cred`, `_enc_key_error`, `_read_account`, `_read_positions`, `_touch_hwm`, `_paper_mismatch`, `_daily_used`, `_recent_duplicate`, `_unresolved`, `_evaluate`, `_summaries`, `_spec`, `_principal`, `_meta`, `_set_meta`, `_uuid_or_none`, `_release_hash`, `_requires_approval`, `_rule_for`, `_account_view`, `_gate_limits`, `_decision_inputs`, `_replay_inputs`, `_close`, `_after`, `_status_outcome`, `_record_fill`, `_apply_alpaca`, `_mark_committee`, `_notify_closed`, `_definitive_reject`, `_committee_memo_ok`, `_send`, `_finish_send`, `_execute`, `_lock`, `_expired`, `_expire_row`, `_needs_human`, `_approval_decision` y 10 más

## Depende de

- [[brokerage.alpaca.py]] — importa `alpaca`
- [[brokerage.crypto.py]] — importa `crypto`
- [[brokerage.models.py]] — importa `BrokerAudit`, `BrokerClient`, `BrokerFill`, `BrokerOAuthState`, `BrokerOrder`, `RISK_PROFILES`, `SOURCES`
- [[brokerage.risk.py]] — importa `risk`
- [[core.__init__.py]] — importa `account`, `focus`, `gates`, `report`
- [[core.config.py]] — importa `FINNHUB`
- [[core.decision_sites.py]] — importa `clean`, `decision_sites`
- [[core.decisions.py]] — importa `decisions`
- [[core.governance.py]] — importa `governance`
- [[core.identity.py]] — importa `identity`
- [[core.ledger.py]] — importa `money_gate`
- [[core.pin.py]] — importa `in_production`
- [[core.quotes.py]] — importa `_fetch_quote_raw`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`
- [[research.committee.py]] — importa `committee`, `mark_executed`, `memo_allows_order`

## Lo usan

- [[brokerage.api.py]] — lo importa
- [[core.prices_store.py]] — lo importa
- [[core.trading_agent.py]] — lo importa
- [[mcp_server.api.py]] — lo importa
- [[mcp_server.auth.py]] — lo importa
- [[mcp_server.oauth.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `cancel_order` → [[API herramientas MCP]]
- herramienta MCP `get_account` → [[API herramientas MCP]]
- herramienta MCP `get_order_status` → [[API herramientas MCP]]
- herramienta MCP `get_positions` → [[API herramientas MCP]]
- herramienta MCP `list_orders` → [[API herramientas MCP]]
- herramienta MCP `preview_order` → [[API herramientas MCP]]
- herramienta MCP `run_committee` → [[API herramientas MCP]]
- herramienta MCP `submit_order` → [[API herramientas MCP]]

_Además lo importan 15 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV TRADE_PIN]]

## Pruebas que lo cubren

- [[tests.test_brokerage.py]]
- [[tests.test_cierre_defectos.py]]
- [[tests.test_gates_orders_parity.py]]
- [[tests.test_impl_registry.py]]
- [[tests.test_ledger_callsites.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_chain.py]]
- [[tests.test_ledger_review_fixes.py]]
- [[tests.test_mcp.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_phase3.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_review_batch_g.py]]
- [[tests.test_security.py]]
- [[tests.test_trading_agent_ledger.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
- [[Sesión 2026-10-13 (d) — PASOS 12, 14, 15-17 Y BLOQUE 2]]
- [[Sesión 2026-10-03 — Cierre de Phase 3]]
