---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/pin.py"
lenguaje: "python"
lineas: 260
aliases: ["core/pin.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/pin.py

> Módulo · capa [[Capa Infraestructura]] · 260 líneas · `core/pin.py`

## Para qué sirve

verificación ÚNICA del PIN de operador (X-Trade-Pin).

## API pública

- `client_ip()` _(línea 73)_
- `on_global_lock(fn)` — Registra un callback(scope, n) para auditar el bloqueo global (idempotente). _(línea 79)_
- `trusted(ip)` — ¿Esta IP acertó el PIN hace < PIN_TRUST_S y tiene < PIN_TRUSTED_MAX_FAILS fallos propios? (la usa mcp_server/auth para su bloqueo propio). _(línea 112)_
- `configured()` _(línea 123)_
- `check(got=…, where=…, strict=…, ip=…)` — Núcleo sin Flask-response: None si el PIN es válido (o no hace falta); si no, (dict_error_bilingüe, status). `got=None` → cabecera … _(línea 133)_
- `pin_error(got=…, where=…, strict=…)` — None si el PIN es válido; si no, (respuesta_json, status). strict=False: sin TRADE_PIN configurado se permite (escrituras de ontología en … _(línea 194)_
- `secret_key_default()` — True si SECRET_KEY falta o es la del repo (pública). _(línea 212)_
- `in_production()` — Railway define RAILWAY_ENVIRONMENT (o \*_NAME / RAILWAY_PROJECT_ID). _(línea 218)_
- `insecure_production_secret()` — En producción con SECRET_KEY por defecto: lo que se firme con ella es falsificable. _(línea 224)_
- `require_pin(f)` _(línea 229)_
- `operator_strict()` — Paso 5 (G-6): en PRODUCCIÓN las escrituras de operador exigen TRADE_PIN configurado (sin él → 403 'deshabilitado'); en desarrollo (sin … _(línea 237)_
- `require_operator(f)` _(línea 243)_

**Internas** (empiezan con `_`): `_prune`, `_lock_left`, `_disabled_body`, `_bind_operator`, `_reset_for_tests`

## Depende de

- [[core.identity.py]] — importa `identity`

## Lo usan

- [[brokerage.api.py]] — lo importa
- [[brokerage.service.py]] — lo importa
- [[core.decide_api.py]] — lo importa
- [[core.decisions.py]] — lo importa
- [[core.governance_api.py]] — lo importa
- [[core.http.py]] — lo importa
- [[core.identity.py]] — lo importa
- [[core.ledger_api.py]] — lo importa
- [[core.ops_check.py]] — lo importa
- [[core.prices_api.py]] — lo importa
- [[matrix.api.py]] — lo importa
- [[mcp_server.api.py]] — lo importa
- [[mcp_server.auth.py]] — lo importa
- [[mcp_server.oauth.py]] — lo importa
- [[ontology.api.py]] — lo importa
- [[research.committee_api.py]] — lo importa
- [[scripts.migrate_v0_to_ontology.py]] — lo importa
- [[server.py]] — lo importa

_Además lo importan 17 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV RAILWAY_ENVIRONMENT]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV RAILWAY_ENVIRONMENT_NAME]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV RAILWAY_PROJECT_ID]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV SECRET_KEY]]
- [[ENV TRADE_PIN]]

## Pruebas que lo cubren

- [[tests.test_cleanup_server.py]]
- [[tests.test_governance.py]]
- [[tests.test_governance_activation.py]]
- [[tests.test_infra.py]]
- [[tests.test_ledger_anchor.py]]
- [[tests.test_ledger_core.py]]
- [[tests.test_ledger_privacy.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_ops_review_steps568.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_overnight_ui_dossier_clients.py]]
- [[tests.test_prices_eod.py]]
- [[tests.test_reconcile.py]]
- [[tests.test_repair_ontology_review.py]]
- [[tests.test_repair_ops.py]]
- [[tests.test_repair_review2.py]]
- [[tests.test_security.py]]
- [[tests.test_trading_agent_ledger.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-09-30 — PHASE 3 + WORLD MONITOR + CORRETAJE + MCP + ENDURECIMIENTO (sw v170)]]
