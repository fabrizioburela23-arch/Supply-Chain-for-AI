---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "brokerage/crypto.py"
lenguaje: "python"
lineas: 135
aliases: ["brokerage/crypto.py"]
tags: ["capa/dinero", "tipo/modulo"]
---

# brokerage/crypto.py

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 135 líneas · `brokerage/crypto.py`

## Para qué sirve

cifrado de credenciales de clientes (Fernet).

## API pública

- clase `CryptoUnavailable` _(línea 30)_
- `key_source()` — 'env' | 'secret_key' | 'default' — para el panel de estado (sin secretos). _(línea 57)_
- `crypto_available()` _(línea 74)_
- `encrypt_json(data)` — dict → token Fernet (str). Lanza CryptoUnavailable si no hay cifrado. _(línea 87)_
- `decrypt_json(token)` — token → dict. Devuelve {} si está vacío; lanza CryptoUnavailable si la clave no coincide (p. ej. cambió BROKERAGE_ENC_KEY/SECRET_KEY). _(línea 100)_
- `mask(value, keep=…)` — 'PKABCDEF1234' → '\*\*\*\*1234'. Nunca devuelve más de `keep` caracteres. _(línea 116)_
- `sign(message)` — HMAC-SHA256 (hex, 32 chars) con una clave derivada de la de cifrado — firma el `state` de OAuth para que no se pueda fabricar. _(línea 126)_
- `verify(message, signature)` _(línea 134)_

**Internas** (empiezan con `_`): `_warn_once`, `_raw_key_material`, `_fernet`, `_in_production`

## Depende de

_Nada interno._

## Lo usan

- [[brokerage.service.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV BROKERAGE_ENC_KEY]]
- [[ENV RAILWAY_ENVIRONMENT]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV RAILWAY_ENVIRONMENT_NAME]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV RAILWAY_PROJECT_ID]] _(en una lista, p. ej. para tapar secretos en logs)_
- [[ENV SECRET_KEY]]

## Pruebas que lo cubren

- [[tests.test_brokerage.py]]
- [[tests.test_security.py]]
