---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "brokerage/models.py"
lenguaje: "python"
lineas: 194
aliases: ["brokerage/models.py"]
tags: ["capa/dinero", "tipo/modulo"]
---

# brokerage/models.py

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 194 líneas · `brokerage/models.py`

## Para qué sirve

tablas del corretaje multi-cliente.

## API pública

- clase `BrokerClient` _(línea 46)_
- clase `BrokerOrder` _(línea 71)_
- clase `BrokerAudit` — APPEND-ONLY. El código de brokerage/ solo hace INSERT aquí. _(línea 117)_
- clase `BrokerOAuthState` _(línea 130)_

**Internas** (empiezan con `_`): `_uuid`, `_safe_ddl`, `_after_create`

## Depende de

- [[ontology.models.py]] — importa `Base`

## Lo usan

- [[brokerage.service.py]] — lo importa
- [[ontology.db.py]] — lo importa

_Además lo importan 4 pruebas (lista abajo)._

## Pruebas que lo cubren

- [[tests.test_brokerage.py]]
- [[tests.test_infra.py]]
- [[tests.test_phase3.py]]
- [[tests.test_security.py]]
