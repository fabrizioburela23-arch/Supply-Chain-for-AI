---
tipo: "modulo"
capa: "MCP y API"
ruta: "mcp_server/auth.py"
lenguaje: "python"
lineas: 534
aliases: ["mcp_server/auth.py"]
tags: ["capa/mcp-api", "tipo/modulo"]
---

# mcp_server/auth.py

> Módulo · capa [[Capa MCP y API]] · 534 líneas · `mcp_server/auth.py`

## Para qué sirve

tokens kmcp_…, alcances, límites por token y auditoría.

## API pública

- `db_available()` _(línea 54)_
- `ensure_late_columns()` — ADD COLUMN IF NOT EXISTS de las columnas añadidas después (idempotente). _(línea 62)_
- `with_schema(fn)` — Si las tablas mcp_\* (o una columna nueva) aún no existen, las crea y reintenta. _(línea 75)_
- clase `BiError` — Error de validación con texto en español E inglés (regla bilingüe). _(línea 92)_
- clase `AuthUnavailable` — La base no respondió al validar un token: NO es un token inválido (→ 503). _(línea 100)_
- `hash_secret(raw)` _(línea 104)_
- `new_token()` _(línea 108)_
- `normalize_scopes(raw)` — Lista ordenada ⊆ SCOPES; 'read' siempre incluido. Acepta lista o 'a b,c'. _(línea 112)_
- `unknown_scopes(raw)` _(línea 121)_
- `client_ip()` — IP para los límites por IP: la que añade el proxy de CONFIANZA (Railway añade/escribe la IP real al final de X-Forwarded-For). El primer … _(línea 128)_
- `pin_policy()` _(línea 153)_
- `pin_strong()` _(línea 158)_
- `pin_locked_for()` — Segundos que quedan de bloqueo global del PIN (0 = libre). _(línea 162)_
- `reset_pin_guard()` — Limpia el bloqueo propio de MCP y el contador COMPARTIDO de core.pin (solo tests / soporte). _(línea 168)_
- `check_pin(got, ip=…, where=…, safety=…)` — → None si el PIN es válido; si no, (dict_error, código_http). _(línea 201)_
- clase `Principal` _(línea 246)_
- `resolve_broker_client(session, client_id)` — Valida el cliente de corretaje → (id canónico, nombre) o lanza ValueError. _(línea 266)_
- `create_token(session, name, scopes, client_id=…, created_by=…, kind=…, expires_at=…, oauth_client_id=…, oauth_code_hash=…)` — → (fila McpToken, token en claro). El token en claro NO se guarda. _(línea 280)_
- `token_dict(row, client_names=…)` _(línea 310)_
- `list_tokens(session, include_revoked=…)` _(línea 345)_
- `revoke_token(session, token_id, actor)` _(línea 355)_
- `authenticate(authorization_header)` — Header Authorization → Principal o None (token ausente, desconocido, revocado o caducado). Si la BASE falla (reinicio de Postgres, pool … _(línea 374)_
- `limits()` _(línea 423)_
- `inflight_acquire(principal)` — → None si hay cupo (llamar luego a inflight_release); si no, 'token' | 'total'. _(línea 439)_
- `inflight_release(principal)` _(línea 453)_
- `allow(principal_or_key, bucket, limit, window)` _(línea 464)_
- `summarize_args(args, depth=…)` — Resumen de argumentos para la auditoría: SIN secretos, acotado. _(línea 471)_
- `write_audit(principal=…, method=…, tool=…, args=…, status=…, error=…, latency_ms=…, ip=…, session_id=…)` _(línea 500)_
- `list_audit(session, limit=…, token_id=…)` _(línea 526)_

**Internas** (empiezan con `_`): `_now`, `_aware`, `_register_pin_fail`, `_brokerage_service`, `_client_names`, `_static_principal`, `_int_env`

## Depende de

- [[brokerage.service.py]] — importa `(dinámico: brokerage.service)`
- [[core.http.py]] — importa `_rate_limit`
- [[core.pin.py]] — importa `pin`
- [[mcp_server.models.py]] — importa `LATE_COLUMNS`, `McpAudit`, `McpToken`
- [[ontology.db.py]] — importa `_get_engine`, `init_schema`, `ontology_available`, `session_scope`

## Lo usan

- [[core.khipu_chat.py]] — lo importa
- [[core.ops_check.py]] — lo importa
- [[mcp_server.api.py]] — lo importa
- [[mcp_server.oauth.py]] — lo importa
- [[mcp_server.tools.py]] — lo importa

_Además lo importan 12 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV MCP_MAX_INFLIGHT]]
- [[ENV MCP_MAX_INFLIGHT_TOTAL]]
- [[ENV MCP_PIN_LOCK_MIN]]
- [[ENV MCP_PIN_MAX_FAILS]]
- [[ENV MCP_RATE_PER_MIN]]
- [[ENV MCP_RESEARCH_PER_HOUR]]
- [[ENV MCP_STATIC_TOKEN]]
- [[ENV MCP_TRADE_PER_HOUR]]
- [[ENV MCP_TRUSTED_PROXY_HOPS]]
- [[ENV TRADE_PIN]]

## Pruebas que lo cubren

- [[tests.test_context_engine.py]]
- [[tests.test_genui_rivals.py]]
- [[tests.test_ledger_callsites_chat.py]]
- [[tests.test_mcp.py]]
- [[tests.test_mcp_contract.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_repair_graph.py]]
- [[tests.test_repair_ops.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_rutas_acceso_decision.py]]
- [[tests.test_security.py]]
- [[tests.test_tensor.py]]
