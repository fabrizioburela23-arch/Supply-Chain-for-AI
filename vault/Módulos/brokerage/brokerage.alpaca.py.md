---
tipo: "modulo"
capa: "Dinero (carteras, trading, corretaje)"
ruta: "brokerage/alpaca.py"
lenguaje: "python"
lineas: 256
aliases: ["brokerage/alpaca.py"]
tags: ["capa/dinero", "tipo/modulo"]
---

# brokerage/alpaca.py

> Módulo · capa [[Capa Dinero (carteras, trading, corretaje)]] · 256 líneas · `brokerage/alpaca.py`

## Para qué sirve

cliente HTTP mínimo de Alpaca (Trading API v2 + OAuth).

## API pública

- clase `AlpacaError` — Error de Alpaca con status HTTP (None = error de red/tiempo agotado). _(línea 45)_
- `clean_env(v)` _(línea 55)_
- `norm_base(v, default=…)` — Normaliza una base de Alpaca igual que server._norm_alpaca_base (quita barra final, /v2, comillas; añade https://) y exige un host oficial. _(línea 59)_
- `base_for_mode(mode)` _(línea 75)_
- `is_paper_base(base)` _(línea 79)_
- `is_crypto(symbol)` _(línea 83)_
- `house_env()` — Credenciales de la casa desde el entorno (o None si faltan). _(línea 87)_
- clase `AlpacaClient` — Cliente fino. Todos los métodos devuelven JSON (dict/list) o lanzan AlpacaError. Nunca incluye claves en los mensajes de error. _(línea 100)_
- `oauth_config()` _(línea 213)_
- `oauth_authorize_url(state, env=…)` _(línea 221)_
- `oauth_exchange(code)` — Canjea el `code` por un token. Devuelve {access_token, token_type, scope} o lanza AlpacaError. El secreto viaja en el cuerpo (lo exige … _(línea 230)_

## Depende de

_Nada interno._

## Lo usan

- [[brokerage.risk.py]] — lo importa
- [[brokerage.service.py]] — lo importa

_Además lo importan 2 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV ALPACA_BASE]]
- [[ENV ALPACA_KEY]]
- [[ENV ALPACA_OAUTH_CLIENT_ID]]
- [[ENV ALPACA_OAUTH_CLIENT_SECRET]]
- [[ENV ALPACA_OAUTH_REDIRECT_URI]]
- [[ENV ALPACA_SECRET]]

## Pruebas que lo cubren

- [[tests.test_brokerage.py]]
- [[tests.test_mcp.py]]
