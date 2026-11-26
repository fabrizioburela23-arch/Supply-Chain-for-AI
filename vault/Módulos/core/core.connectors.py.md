---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/connectors.py"
lenguaje: "python"
lineas: 231
aliases: ["core/connectors.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/connectors.py

> Módulo · capa [[Capa Infraestructura]] · 231 líneas · `core/connectors.py`

## Para qué sirve

🧩 CONECTORES: Khipus usa tus apps (Gmail, Sheets, Slack, Notion, Calendar…) por UNA sola puerta, Composio (2026-11-26, pedido de Fabrizio: «algo que se conecte a todo, sin un MCP por cada cosa»).

## API pública

- `api_key()` _(línea 47)_
- `enabled()` _(línea 51)_
- `base()` _(línea 55)_
- `user_id(owner_key_or_hash)` — La persona en Composio: huella estable y opaca de la llave del navegador (nunca la llave). _(línea 59)_
- clase `ConnectorError` _(línea 67)_
- `is_write(slug, description=…)` — ¿La acción CAMBIA algo fuera de Khipus? Ante la duda, sí (pedir confirmación nunca hace daño). _(línea 94)_
- `search_tools(query, app=…, limit=…, http=…)` _(línea 117)_
- `connections(uid, http=…)` — {app: status} de las apps que esta persona conectó. _(línea 134)_
- `connect_link(uid, app, callback_url=…, http=…)` _(línea 166)_
- `execute(uid, slug, arguments, http=…)` _(línea 180)_
- `propose(uid, slug, app, arguments, summary)` _(línea 196)_
- `pending(uid)` _(línea 208)_
- `take(uid, pid)` — Saca la pendiente (una sola vez) si es de esta persona. _(línea 216)_
- `drop(uid, pid)` _(línea 226)_
- `status()` _(línea 230)_

**Internas** (empiezan con `_`): `_req`, `_clip`, `_params_summary`, `_auth_config`, `_gc`

## Depende de

_Nada interno._

## Lo usan

- [[core.connectors_api.py]] — lo importa
- [[core.khipu_chat.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Variables de entorno que lee (solo nombres)

- [[ENV COMPOSIO_API_KEY]]
- [[ENV COMPOSIO_BASE]]
- [[ENV COMPOSIO_ENABLED]]
- [[ENV COMPOSIO_KEY]]

## Pruebas que lo cubren

- [[tests.test_connectors.py]]

## Mencionado en sesiones de trabajo

- [[Sesión 2026-10-16 — PRÓXIMA SESIÓN — EMPEZAR AQUÍ]]
