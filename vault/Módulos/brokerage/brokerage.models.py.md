---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "brokerage/models.py"
lenguaje: "python"
lineas: 234
aliases: ["brokerage/models.py"]
tags: ["capa/dinero", "tipo/modulo"]
---

# brokerage/models.py

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 234 líneas · `brokerage/models.py`

## Para qué sirve

tablas del corretaje multi-cliente.

## API pública

- clase `BrokerClient` _(línea 53)_
- clase `BrokerOrder` _(línea 78)_
- clase `BrokerAudit` — APPEND-ONLY. El código de brokerage/ solo hace INSERT aquí. _(línea 128)_
- clase `BrokerFill` — APPEND-ONLY (kh_append_only, core/ledger_ddl.APPEND_ONLY_TABLES). Avance de ejecución observado. _(línea 141)_
- clase `BrokerOAuthState` _(línea 164)_

**Internas** (empiezan con `_`): `_uuid`, `_safe_ddl`, `_after_create`

## Depende de

- [[core.ledger_ddl.py]] — importa `safe_ddl`
- [[ontology.models.py]] — importa `Base`

## Lo usan

- [[brokerage.service.py]] — lo importa
- [[ontology.db.py]] — lo importa

_Además lo importan 15 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_brokerage.py]]
- [[tests.test_cierre_infra.py]]
- [[tests.test_import_roundtrip.py]]
- [[tests.test_infra.py]]
- [[tests.test_ledger_callsites.py]]
- [[tests.test_ledger_callsites_committee.py]]
- [[tests.test_ledger_guard.py]]
- [[tests.test_ledger_review_fixes.py]]
- [[tests.test_ops_identity.py]]
- [[tests.test_order_single_path.py]]
- [[tests.test_phase3.py]]
- [[tests.test_replay_determinism.py]]
- [[tests.test_security.py]]
- [[tests.test_trading_agent_ledger.py]]
- [[tests.test_voice_agent_split.py]]
