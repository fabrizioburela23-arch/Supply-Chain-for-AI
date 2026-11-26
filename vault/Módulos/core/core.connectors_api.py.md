---
tipo: "modulo"
capa: "Infraestructura"
ruta: "core/connectors_api.py"
lenguaje: "python"
lineas: 108
aliases: ["core/connectors_api.py"]
tags: ["capa/infraestructura", "tipo/modulo"]
---

# core/connectors_api.py

> Módulo · capa [[Capa Infraestructura]] · 108 líneas · `core/connectors_api.py`

## Para qué sirve

/api/connectors/\* : la ventana 🧩 Conectores (engine/connectors.js) habla con esto.

## API pública

- `status()` _(línea 37)_
- `pending_list()` — Ligero (no llama a Composio): lo consulta engine/connectors.js para pedir confirmación al instante. _(línea 54)_
- `link()` _(línea 62)_
- `confirm()` _(línea 75)_
- `discard()` _(línea 106)_

**Internas** (empiezan con `_`): `_uid`, `_body`, `_err`

## Depende de

- [[core.connectors.py]] — importa `connectors`
- [[core.decision_sites.py]] — importa `decision_sites`
- [[core.http.py]] — importa `rate_limit`
- [[core.pin.py]] — importa `pin_error`
- [[ontology.db.py]] — importa `ontology_available`, `session_scope`

## Lo usan

- [[server.py]] — lo importa

_Además lo importan 1 pruebas (lista abajo)._

## Endpoints que define

| Método | Ruta | Función | Lo llaman |
|---|---|---|---|
| `POST` | `/api/connectors/confirm` | `confirm` | [[engine.connectors.js]], 1 prueba |
| `POST` | `/api/connectors/discard` | `discard` | [[engine.connectors.js]], 1 prueba |
| `POST` | `/api/connectors/link` | `link` | [[engine.connectors.js]] |
| `GET` | `/api/connectors/pending` | `pending_list` | [[engine.connectors.js]], 1 prueba |
| `GET` | `/api/connectors/status` | `status` | [[engine.connectors.js]] |

Grupos: [[API connectors]]

## Pruebas que lo cubren

- [[tests.test_connectors.py]]
