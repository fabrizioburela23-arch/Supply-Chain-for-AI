---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "brokerage/service.py"
lenguaje: "python"
lineas: 1530
aliases: ["brokerage/service.py"]
tags: ["capa/dinero", "tipo/modulo"]
---

# brokerage/service.py

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 1.530 líneas · `brokerage/service.py`

## Para qué sirve

lógica del corretaje multi-cliente (CONTRATO COMPARTIDO).

## API pública

- `available()` — ¿Se puede usar el corretaje? (requiere la base de la ontología). _(línea 71)_
- `approval_ttl_s()` _(línea 128)_
- `audit(session, actor, action, client_id=…, order_id=…, detail=…)` — APPEND-ONLY. Jamás se escribe un secreto en `detail`. Desde el paso 5 cada fila lleva `detail._who` (principal autenticado + canal) aunque … _(línea 155)_
- `list_audit(session, client_id=…, limit=…)` _(línea 167)_
- `account_fingerprint(rec)` — Huella de la cuenta REAL detrás del cliente (modo + URL + credenciales). Se guarda en cada previsualización: si cambia antes de ejecutar … _(línea 185)_
- `client_dict(rec)` — Vista pública del cliente — SIN secretos (solo el hint enmascarado). _(línea 199)_
- `ensure_house_client(session)` — Registra la cuenta de la casa (ALPACA_KEY/SECRET/BASE) como cliente «Cuenta principal» si hay credenciales en el entorno. Idempotente y a … _(línea 249)_
- `list_clients(session)` _(línea 285)_
- `get_client(session, client_id)` _(línea 317)_
- `create_client(session, name, email=…, notes=…, mode=…, risk_profile=…, limits=…, mandate=…, actor=…)` _(línea 358)_
- `update_client(session, client_id, patch, actor=…)` _(línea 386)_
- `pause_client(session, client_id, actor=…)` _(línea 464)_
- `resume_client(session, client_id, actor=…)` _(línea 468)_
- `make_alpaca(rec)` — AlpacaClient para el cliente (los tests lo sustituyen por uno falso). _(línea 475)_
- `set_credentials(session, client_id, api_key, api_secret, env=…, actor=…, verify=…)` _(línea 517)_
- `account_snapshot(session, client_id)` _(línea 604)_
- `reference_price(alp, symbol, positions)` — (precio, fuente) de MERCADO para estimar montos — nunca inventado: posición en Alpaca → último trade de Alpaca → Finnhub. (None, None) si … _(línea 627)_
- `market_clock(alp)` _(línea 654)_
- `daily_used(session, client_id)` — Público (lo lee el comité): US\$ comprados hoy por el cliente. _(línea 677)_
- `order_dict(row, client_name=…)` _(línea 852)_
- `preview_order(session, client_id, symbol, side, notional=…, qty=…, order_type=…, limit_price=…, source=…, requested_by=…, proposal_id=…, rationale=…)` _(línea 875)_
- `confirm_order(session, preview_id, approved_by, source=…)` _(línea 1147)_
- `approve_preview(session, preview_id, approved_by)` — Aprobación HUMANA (la ruta exige PIN) de una propuesta de MCP/comité. _(línea 1201)_
- `reject_preview(session, preview_id, actor, reason=…)` _(línea 1220)_
- `pending_approvals(session)` _(línea 1244)_
- `list_orders(session, client_id=…, status=…, limit=…)` _(línea 1262)_
- `get_order(session, order_id)` _(línea 1275)_
- `cancel_order(session, order_id, actor)` _(línea 1318)_
- `sync_orders(session, client_id=…, actor=…)` — Actualiza desde Alpaca el estado de las órdenes abiertas, y reconcilia por client_order_id las que quedaron con estado desconocido (sin id … _(línea 1366)_
- `oauth_start(session, client_id, env=…, actor=…)` _(línea 1412)_
- `oauth_callback(session, state, code, error=…)` — Valida el `state` (firmado, de un solo uso, < 15 min), canjea el código y guarda el token CIFRADO. Devuelve {ok, client_id, client_name, … _(línea 1439)_
- `public_status()` — Lo único que se muestra SIN PIN. _(línea 1496)_
- `status_info()` — Detalle de configuración (va detrás del PIN: revela la postura de seguridad). _(línea 1501)_

**Internas** (empiezan con `_`): `_now`, `_iso`, `_f`, `_aware`, `_err`, `_not_found`, `_Bad`, `_sha`, `_who`, `_connected`, `_expire_open`, `_account_changed`, `_lookup`, `_client_rec`, `_name_taken`, `_clean_limits`, `_clean_mandate`, `_valid_cred`, `_enc_key_error`, `_read_account`, `_read_positions`, `_touch_hwm`, `_paper_mismatch`, `_daily_used`, `_recent_duplicate`, `_unresolved`, `_evaluate`, `_summaries`, `_spec`, `_apply_alpaca`, `_mark_committee`, `_notify_closed`, `_definitive_reject`, `_committee_memo_ok`, `_execute`, `_lock`, `_expired`, `_expire_row`, `_needs_human`, `_names`, `_age_s`, `_reconcile_unknown`

## Depende de

- [[brokerage.alpaca.py]] — importa `alpaca`
- [[brokerage.crypto.py]] — importa `crypto`
- [[brokerage.models.py]] — importa `BrokerAudit`, `BrokerClient`, `BrokerOAuthState`, `BrokerOrder`, `RISK_PROFILES`, `SOURCES`
- [[brokerage.risk.py]] — importa `risk`
- [[core.config.py]] — importa `FINNHUB`
- [[core.identity.py]] — importa `identity`
- [[core.quotes.py]] — importa `_fetch_quote_raw`
- [[ontology.db.py]] — importa `ontology_available`
- [[research.committee.py]] — importa `committee`, `mark_executed`, `memo_allows_order`

## Lo usan

- [[brokerage.api.py]] — lo importa
- [[mcp_server.api.py]] — lo importa
- [[mcp_server.auth.py]] — lo importa
- [[mcp_server.oauth.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa
- [[research.committee.py]] — lo importa
- [[server.py]] — lo importa
- herramienta MCP `cancel_order` → [[API herramientas MCP]]
- herramienta MCP `get_account` → [[API herramientas MCP]]
- herramienta MCP `get_order_status` → [[API herramientas MCP]]
- herramienta MCP `get_positions` → [[API herramientas MCP]]
- herramienta MCP `list_orders` → [[API herramientas MCP]]
- herramienta MCP `preview_order` → [[API herramientas MCP]]
- herramienta MCP `run_committee` → [[API herramientas MCP]]
- herramienta MCP `submit_order` → [[API herramientas MCP]]

_Además lo importan 6 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV BROKERAGE_APPROVAL_TTL_MIN]]
- [[ENV TRADE_PIN]]

## Pruebas que lo cubren

- [[tests.test_brokerage.py]]
- [[tests.test_ledger_chain.py]]
- [[tests.test_mcp.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_phase3.py]]
- [[tests.test_security.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-03 — Cierre de Phase 3]]
